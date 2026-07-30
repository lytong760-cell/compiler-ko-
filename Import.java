import java.io.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.regex.Pattern;

public class Import {
    private static final String MODULES_DIR = System.getenv("KO_MODULES_PATH") != null
        ? System.getenv("KO_MODULES_PATH")
        : System.getProperty("user.home") + "/.ko/modules";

    private static final String SIGNATURE_ALGO = "SHA-256";

    private static final Set<String> ALLOWED_MODULES = new HashSet<>(Arrays.asList(
        "Random", "Os", "Website"
    ));

    private static final Pattern SAFE_PATH = Pattern.compile("^[a-zA-Z0-9_./-]+$");

    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: Import <moduleName> <alias> [scopeTag]");
            System.exit(1);
        }

        String moduleName = args[0];
        String alias = args[1];
        String scopeTag = args.length > 2 ? args[2] : "global";

        try {
            validateModuleName(moduleName);
            ImportResult result = resolveAndVerify(moduleName, alias, scopeTag);
            System.out.println(result.toJson());
        } catch (SecurityException e) {
            System.err.println("Security error: " + e.getMessage());
            System.exit(3);
        } catch (Exception e) {
            System.err.println("Import error: " + e.getMessage());
            System.exit(2);
        }
    }

    static void validateModuleName(String moduleName) throws SecurityException {
        if (moduleName == null || moduleName.isEmpty()) {
            throw new SecurityException("Module name cannot be empty");
        }
        if (!SAFE_PATH.matcher(moduleName).matches()) {
            throw new SecurityException("Invalid module name: contains unsafe characters");
        }
        if (moduleName.contains("..") || moduleName.startsWith("/") || moduleName.startsWith("~")) {
            throw new SecurityException("Path traversal detected in module name");
        }
        if (!ALLOWED_MODULES.contains(moduleName)) {
            throw new SecurityException("Module '" + moduleName + "' is not in the allowed module list");
        }
    }

    static ImportResult resolveAndVerify(String moduleName, String alias, String scopeTag)
            throws Exception {
        Path moduleDir = Paths.get(MODULES_DIR);
        if (!Files.exists(moduleDir)) {
            Files.createDirectories(moduleDir);
        }

        Path modulePath = moduleDir.resolve(moduleName + ".ko");
        if (!Files.exists(modulePath)) {
            modulePath = moduleDir.resolve(moduleName + ".java");
        }
        if (!Files.exists(modulePath)) {
            modulePath = moduleDir.resolve(moduleName + ".py");
        }

        String absolutePath = modulePath.toAbsolutePath().toString();
        String moduleHash = computeFileHash(modulePath);

        if (modulePath.toFile().length() == 0) {
            throw new SecurityException("Empty module file: " + moduleName);
        }

        String scopeTable = ingestScopeTable(modulePath, scopeTag);

        return new ImportResult(moduleName, alias, scopeTag, absolutePath, moduleHash, scopeTable);
    }

    static String computeFileHash(Path path) throws Exception {
        if (!Files.exists(path)) {
            return "MODULE_NOT_FOUND";
        }
        byte[] fileBytes = Files.readAllBytes(path);
        MessageDigest digest = MessageDigest.getInstance(SIGNATURE_ALGO);
        byte[] hash = digest.digest(fileBytes);
        StringBuilder hex = new StringBuilder();
        for (byte b : hash) {
            hex.append(String.format("%02x", b));
        }
        return hex.toString();
    }

    static String ingestScopeTable(Path modulePath, String scopeTag) throws Exception {
        if (!Files.exists(modulePath)) {
            return "scope_" + scopeTag + ":{module:" + modulePath.getFileName() + ",resolved:false}";
        }

        String content = new String(Files.readAllBytes(modulePath), "UTF-8");
        Set<String> exportedSymbols = new LinkedHashSet<>();

        for (String line : content.split("\n")) {
            String trimmed = line.trim();
            if (trimmed.isEmpty() || trimmed.startsWith("|") || trimmed.startsWith("//")) {
                continue;
            }
            if (trimmed.contains("public") || trimmed.contains("export") || trimmed.contains("def ")
                    || trimmed.matches(".*\\bfunction\\b.*") || trimmed.matches(".*\\bclass\\b.*")) {
                String[] parts = trimmed.split("[\\s(]+");
                for (String part : parts) {
                    part = part.trim();
                    if (part.matches("[a-zA-Z_][a-zA-Z0-9_]*") && !part.equals("public")
                            && !part.equals("export") && !part.equals("def") && !part.equals("class")
                            && !part.equals("function") && !part.equals("return")) {
                        exportedSymbols.add(part);
                    }
                }
            }
        }

        StringBuilder sb = new StringBuilder();
        sb.append("scope_").append(scopeTag).append(":");
        sb.append("{module:").append(modulePath.getFileName());
        sb.append(",hash:").append(computeFileHash(modulePath));
        sb.append(",symbols:[");
        boolean first = true;
        for (String sym : exportedSymbols) {
            if (!first) sb.append(",");
            sb.append(sym);
            first = false;
        }
        sb.append("]}");

        return sb.toString();
    }

    static class ImportResult {
        String moduleName;
        String alias;
        String scopeTag;
        String resolvedPath;
        String moduleHash;
        String scopeTable;

        ImportResult(String moduleName, String alias, String scopeTag,
                String resolvedPath, String moduleHash, String scopeTable) {
            this.moduleName = moduleName;
            this.alias = alias;
            this.scopeTag = scopeTag;
            this.resolvedPath = resolvedPath;
            this.moduleHash = moduleHash;
            this.scopeTable = scopeTable;
        }

        String toJson() {
            StringBuilder sb = new StringBuilder();
            sb.append("{");
            sb.append("\"module\":\"").append(escape(moduleName)).append("\",");
            sb.append("\"alias\":\"").append(escape(alias)).append("\",");
            sb.append("\"scopeTag\":\"").append(escape(scopeTag)).append("\",");
            sb.append("\"path\":\"").append(escape(resolvedPath)).append("\",");
            sb.append("\"hash\":\"").append(moduleHash).append("\",");
            sb.append("\"scopeTable\":\"").append(escape(scopeTable)).append("\"");
            sb.append("}");
            return sb.toString();
        }

        String escape(String s) {
            return s.replace("\\", "\\\\").replace("\"", "\\\"");
        }
    }
}