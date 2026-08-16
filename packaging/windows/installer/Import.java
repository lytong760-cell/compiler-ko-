/**
 * Import.java - Hybrid Import Subsystem for .ko Language
 * 
 * Supports both built-in local modules and external libraries from ko-studio.ai.studio.
 * 
 * Usage:
 *   java Import <module_name> <alias> <scope_tag>  - Resolve module metadata
 *   java Import install <module_name>               - Install external library
 */

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import java.security.*;

public class Import {

    // Configuration
    private static final String STUDIO_API_BASE = "https://ko-studio.ai.studio/api/v1";
    private static final int CONNECT_TIMEOUT = 10000;
    private static final int READ_TIMEOUT = 30000;
    private static final int MAX_REDIRECTS = 5;
    private static final long MAX_MODULE_SIZE = 50 * 1024 * 1024;

    // Built-in modules that ship with the compiler
    private static final Set<String> BUILTIN_MODULES = Set.of("Random", "Os", "Website");

    // Security: allowed URL schemes
    private static final Set<String> ALLOWED_SCHEMES = Set.of("https");
    private static final Set<String> BANNED_SCHEMES = Set.of("file", "ftp", "jar");

    private static final Map<String, ModuleInfo> moduleCache = new HashMap<>();

    public static void main(String[] args) {
        if (args.length < 1) {
            printError("Usage: Import <module_name> <alias> <scope_tag> | Import install <module_name>");
            System.exit(1);
        }

        try {
            if ("install".equalsIgnoreCase(args[0])) {
                if (args.length < 2) {
                    printError("Usage: Import install <module_name>");
                    System.exit(1);
                }
                installLibrary(args[1]);
                System.exit(0);
            } else {
                if (args.length < 3) {
                    printError("Usage: Import <module_name> <alias> <scope_tag>");
                    System.exit(1);
                }

                String moduleName = args[0];
                String alias = args[1];
                String scopeTag = args[2];

                ModuleInfo moduleInfo = resolveModule(moduleName, scopeTag);
                if (moduleInfo == null) {
                    printError("Module not found: " + moduleName);
                    System.exit(1);
                }

                moduleInfo.alias = alias;
                moduleInfo.scope_tag = scopeTag;
                System.out.println(moduleInfo.toJson());
            }
        } catch (Exception e) {
            printError("Import failed: " + e.getMessage());
            System.exit(1);
        }
    }

    /**
     * Resolves a module by checking built-in modules first, then web registry.
     */
    private static ModuleInfo resolveModule(String moduleName, String scopeTag) throws Exception {
        String cacheKey = moduleName + ":" + scopeTag;
        if (moduleCache.containsKey(cacheKey)) {
            return moduleCache.get(cacheKey);
        }

        if (!isValidModuleName(moduleName)) {
            throw new SecurityException("Invalid module name: " + moduleName);
        }

        // Step 1: Check built-in modules
        if (BUILTIN_MODULES.contains(moduleName)) {
            ModuleInfo info = createBuiltinModuleInfo(moduleName, scopeTag);
            moduleCache.put(cacheKey, info);
            return info;
        }

        // Step 2: Check local modules directory
        ModuleInfo local = resolveLocalModule(moduleName, scopeTag);
        if (local != null) {
            moduleCache.put(cacheKey, local);
            return local;
        }

        // Step 3: Query ko-studio.ai.studio web registry
        ModuleInfo web = resolveWebModule(moduleName, scopeTag);
        if (web != null) {
            moduleCache.put(cacheKey, web);
            return web;
        }

        return null;
    }

    /**
     * Creates ModuleInfo for built-in compiler modules.
     */
    private static ModuleInfo createBuiltinModuleInfo(String moduleName, String scopeTag) {
        ModuleInfo info = new ModuleInfo();
        info.name = moduleName;
        info.module = moduleName;
        info.version = "builtin";
        info.scope_tag = scopeTag;

        switch (moduleName) {
            case "Random":
                info.description = "Built-in random number generation module";
                info.exports = new LinkedHashMap<>();
                info.exports.put("functions", List.of("random_int"));
                break;
            case "Os":
                info.description = "Built-in OS interaction module";
                info.exports = new LinkedHashMap<>();
                info.exports.put("functions", List.of("read_file", "write_file", "list_dir"));
                break;
            case "Website":
                info.description = "Built-in web fetching module";
                info.exports = new LinkedHashMap<>();
                info.exports.put("functions", List.of("fetch", "domain", "status"));
                break;
        }

        return info;
    }

    /**
     * Resolves a module from local modules directory.
     */
    private static ModuleInfo resolveLocalModule(String moduleName, String scopeTag) throws Exception {
        Path modulesDir = getModulesDir();
        if (!Files.exists(modulesDir)) {
            return null;
        }

        String[] extensions = {".ko", ".java", ".py"};
        for (String ext : extensions) {
            Path modulePath = modulesDir.resolve(moduleName + ext);
            if (Files.exists(modulePath)) {
                long fileSize = Files.size(modulePath);
                if (fileSize > MAX_MODULE_SIZE || fileSize == 0) {
                    continue;
                }

                String hash = computeFileHash(modulePath);
                String scopeTable = ingestScopeTable(modulePath, scopeTag);

                ModuleInfo info = new ModuleInfo();
                info.name = moduleName;
                info.module = moduleName;
                info.version = "local";
                info.scope_tag = scopeTag;
                info.resolvedPath = modulePath.toString();
                info.moduleHash = hash;
                info.scopeTable = scopeTable;
                info.description = "Local module: " + modulePath.getFileName();

                return info;
            }
        }

        return null;
    }

    /**
     * Resolves a module from ko-studio.ai.studio web registry.
     */
    private static ModuleInfo resolveWebModule(String moduleName, String scopeTag) throws Exception {
        String apiUrl = STUDIO_API_BASE + "/modules/" + URLEncoder.encode(moduleName, StandardCharsets.UTF_8);
        if (scopeTag != null && !scopeTag.isEmpty()) {
            apiUrl += "?scope=" + URLEncoder.encode(scopeTag, StandardCharsets.UTF_8);
        }

        URL url = new URL(apiUrl);
        if (!ALLOWED_SCHEMES.contains(url.getProtocol().toLowerCase())) {
            throw new SecurityException("URL scheme not allowed: " + url.getProtocol());
        }
        if (BANNED_SCHEMES.contains(url.getProtocol().toLowerCase())) {
            throw new SecurityException("URL scheme is banned: " + url.getProtocol());
        }

        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(CONNECT_TIMEOUT);
        connection.setReadTimeout(READ_TIMEOUT);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("User-Agent", "ko-compiler/2.800");
        connection.setRequestProperty("Accept", "application/json");

        int redirects = 0;
        while (redirects < MAX_REDIRECTS) {
            int responseCode = connection.getResponseCode();

            if (responseCode >= 300 && responseCode < 400) {
                String location = connection.getHeaderField("Location");
                if (location == null) {
                    throw new IOException("Redirect without Location header");
                }

                URL redirectUrl = new URL(url, location);
                if (!ALLOWED_SCHEMES.contains(redirectUrl.getProtocol().toLowerCase())) {
                    throw new SecurityException("Redirect to disallowed scheme: " + redirectUrl.getProtocol());
                }

                connection = (HttpURLConnection) redirectUrl.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(CONNECT_TIMEOUT);
                connection.setReadTimeout(READ_TIMEOUT);
                connection.setInstanceFollowRedirects(false);
                connection.setRequestProperty("User-Agent", "ko-compiler/2.800");
                connection.setRequestProperty("Accept", "application/json");
                redirects++;
                continue;
            }

            if (responseCode == 200) {
                break;
            }

            if (responseCode == 404) {
                return null;
            }

            throw new IOException("HTTP " + responseCode + ": " + connection.getResponseMessage());
        }

        StringBuilder response = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
        }

        return parseModuleJson(response.toString(), moduleName);
    }

    /**
     * Installs a library from ko-studio.ai.studio.
     */
    private static void installLibrary(String moduleName) throws Exception {
        printError("Installing library: " + moduleName);

        if (!isValidModuleName(moduleName)) {
            throw new SecurityException("Invalid module name: " + moduleName);
        }

        if (BUILTIN_MODULES.contains(moduleName)) {
            printError("Module '" + moduleName + "' is a built-in module. No installation needed.");
            return;
        }

        printError("Step 1: Querying ko-studio.ai.studio...");
        String apiUrl = STUDIO_API_BASE + "/modules/" + URLEncoder.encode(moduleName, StandardCharsets.UTF_8);
        URL url = new URL(apiUrl);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(CONNECT_TIMEOUT);
        connection.setReadTimeout(READ_TIMEOUT);
        connection.setRequestProperty("User-Agent", "ko-compiler/2.800");
        connection.setRequestProperty("Accept", "application/json");

        if (connection.getResponseCode() != 200) {
            throw new IOException("Module not found on ko-studio.ai.studio");
        }

        StringBuilder response = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
        }

        String githubUrl = extractJsonValue(response.toString(), "github_url");
        if (githubUrl == null || githubUrl.isEmpty()) {
            throw new IOException("No GitHub URL found for module: " + moduleName);
        }
        printError("Found GitHub URL: " + githubUrl);

        printError("Step 2: Cloning repository...");
        Path tempDir = Files.createTempDirectory("ko-install-" + moduleName);
        Path cloneDir = tempDir.resolve(moduleName);

        try {
            cloneRepository(githubUrl, cloneDir);

            printError("Step 3: Looking for .zip package...");
            Path zipFile = findZipFile(cloneDir);

            if (zipFile == null) {
                throw new IOException("No .zip package found in repository. Installation aborted.");
            }
            printError("Found package: " + zipFile.getFileName());

            printError("Step 4: Cleaning repository...");
            deleteExceptZip(cloneDir, zipFile);

            printError("Step 5: Extracting package...");
            Path modulesDir = getModulesDir();
            Files.createDirectories(modulesDir);
            Path targetDir = modulesDir.resolve(moduleName);

            if (Files.exists(targetDir)) {
                deleteDirectory(targetDir);
            }
            Files.createDirectories(targetDir);
            extractZip(zipFile, targetDir);

            printError("Step 6: Verifying installation...");
            boolean verified = verifyInstallation(targetDir, moduleName);
            if (!verified) {
                throw new IOException("Installation verification failed for module: " + moduleName);
            }

            printError("Library '" + moduleName + "' installed successfully!");

        } finally {
            deleteDirectory(tempDir);
        }
    }

    private static void cloneRepository(String repoUrl, Path targetDir) throws Exception {
        URL url = new URL(repoUrl);
        if (!"https".equalsIgnoreCase(url.getProtocol())) {
            throw new SecurityException("Only HTTPS GitHub URLs are allowed");
        }

        ProcessBuilder pb = new ProcessBuilder(
            "git", "clone", "--depth", "1", repoUrl, targetDir.toString()
        );
        pb.redirectErrorStream(true);
        Process process = pb.start();

        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }

        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new IOException("git clone failed (exit " + exitCode + "): " + output.toString());
        }
    }

    private static Path findZipFile(Path dir) throws IOException {
        if (!Files.isDirectory(dir)) {
            return null;
        }
        try (var stream = Files.walk(dir)) {
            return stream
                .filter(p -> !Files.isDirectory(p))
                .filter(p -> p.toString().toLowerCase().endsWith(".zip"))
                .findFirst()
                .orElse(null);
        }
    }

    private static void deleteExceptZip(Path dir, Path keepZip) throws IOException {
        if (!Files.isDirectory(dir)) {
            return;
        }
        try (var stream = Files.walk(dir)) {
            List<Path> toDelete = stream
                .filter(p -> !p.equals(keepZip))
                .toList();
            for (Path p : toDelete) {
                if (Files.isDirectory(p)) {
                    deleteDirectory(p);
                } else {
                    Files.delete(p);
                }
            }
        }
    }

    private static void deleteDirectory(Path dir) throws IOException {
        if (!Files.exists(dir)) {
            return;
        }
        try (var stream = Files.walk(dir)) {
            List<Path> paths = stream.toList();
            Collections.reverse(paths);
            for (Path p : paths) {
                Files.delete(p);
            }
        }
    }

    private static void extractZip(Path zipFile, Path targetDir) throws IOException {
        try (ZipInputStream zis = new ZipInputStream(
                new BufferedInputStream(Files.newInputStream(zipFile)))) {
            ZipEntry entry;
            byte[] buffer = new byte[8192];

            while ((entry = zis.getNextEntry()) != null) {
                Path entryPath = targetDir.resolve(entry.getName()).normalize();

                if (!entryPath.startsWith(targetDir.normalize())) {
                    throw new SecurityException("Zip entry attempts path traversal: " + entry.getName());
                }

                if (entry.isDirectory()) {
                    Files.createDirectories(entryPath);
                } else {
                    Files.createDirectories(entryPath.getParent());
                    try (OutputStream os = new BufferedOutputStream(Files.newOutputStream(entryPath))) {
                        int len;
                        while ((len = zis.read(buffer)) > 0) {
                            os.write(buffer, 0, len);
                        }
                    }
                }
                zis.closeEntry();
            }
        }
    }

    private static boolean verifyInstallation(Path moduleDir, String moduleName) {
        String[] possibleFiles = {
            moduleName + ".ko", moduleName + ".java", moduleName + ".py",
            "main.ko", "Main.ko"
        };

        for (String filename : possibleFiles) {
            if (Files.exists(moduleDir.resolve(filename))) {
                return true;
            }
        }

        try (var stream = Files.walk(moduleDir)) {
            return stream
                .filter(p -> !Files.isDirectory(p))
                .anyMatch(p -> {
                    String name = p.toString().toLowerCase();
                    return name.endsWith(".ko") || name.endsWith(".java") || name.endsWith(".py");
                });
        } catch (IOException e) {
            return false;
        }
    }

    private static Path getModulesDir() {
        String modulesPath = System.getenv("KO_MODULES_PATH");
        if (modulesPath != null && !modulesPath.isEmpty()) {
            return Paths.get(modulesPath);
        }
        return Paths.get(System.getProperty("user.home"), ".ko", "modules");
    }

    private static boolean isValidModuleName(String name) {
        if (name == null || name.isEmpty() || name.length() > 100) {
            return false;
        }
        return name.matches("^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$") || 
               name.matches("^[a-zA-Z0-9]$");
    }

    private static String computeFileHash(Path path) throws Exception {
        if (!Files.exists(path)) {
            return "MODULE_NOT_FOUND";
        }
        byte[] fileBytes = Files.readAllBytes(path);
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(fileBytes);
        StringBuilder hex = new StringBuilder();
        for (byte b : hash) {
            hex.append(String.format("%02x", b));
        }
        return hex.toString();
    }

    private static String ingestScopeTable(Path modulePath, String scopeTag) throws Exception {
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

    private static ModuleInfo parseModuleJson(String json, String moduleName) {
        ModuleInfo info = new ModuleInfo();
        info.name = moduleName;
        info.module = moduleName;

        try {
            info.version = extractJsonValue(json, "version");
            if (info.version == null) info.version = "1.0.0";

            String exportsJson = extractJsonObject(json, "exports");
            if (exportsJson != null) {
                info.exports = parseExports(exportsJson);
            }

            String depsJson = extractJsonObject(json, "dependencies");
            if (depsJson != null) {
                info.dependencies = parseDependencies(depsJson);
            }

            info.source = extractJsonValue(json, "source");
            info.description = extractJsonValue(json, "description");
            info.author = extractJsonValue(json, "author");
            info.license = extractJsonValue(json, "license");

        } catch (Exception e) {
            System.err.println("Warning: Failed to parse module JSON: " + e.getMessage());
        }

        return info;
    }

    private static Map<String, Object> parseExports(String json) {
        Map<String, Object> exports = new LinkedHashMap<>();
        String functionsJson = extractJsonArray(json, "functions");
        if (functionsJson != null) {
            exports.put("functions", parseStringArray(functionsJson));
        }
        String classesJson = extractJsonArray(json, "classes");
        if (classesJson != null) {
            exports.put("classes", parseStringArray(classesJson));
        }
        String constantsJson = extractJsonObject(json, "constants");
        if (constantsJson != null) {
            exports.put("constants", parseConstants(constantsJson));
        }
        return exports;
    }

    private static List<String> parseDependencies(String json) {
        String depsArray = extractJsonArray(json, "dependencies");
        if (depsArray != null) {
            return parseStringArray(depsArray);
        }
        return new ArrayList<>();
    }

    private static List<String> parseStringArray(String jsonArray) {
        List<String> result = new ArrayList<>();
        String content = jsonArray.trim();
        if (content.startsWith("[") && content.endsWith("]")) {
            content = content.substring(1, content.length() - 1);
        }
        if (!content.isEmpty()) {
            String[] items = content.split(",");
            for (String item : items) {
                String trimmed = item.trim();
                if (trimmed.startsWith("\"") && trimmed.endsWith("\"")) {
                    trimmed = trimmed.substring(1, trimmed.length() - 1);
                }
                result.add(trimmed);
            }
        }
        return result;
    }

    private static Map<String, Object> parseConstants(String json) {
        return new LinkedHashMap<>();
    }

    private static String extractJsonValue(String json, String key) {
        String pattern = "\"" + key + "\"\\s*:\\s*\"([^\"]*)\"";
        java.util.regex.Pattern p = java.util.regex.Pattern.compile(pattern);
        java.util.regex.Matcher m = p.matcher(json);
        if (m.find()) {
            return m.group(1);
        }
        return null;
    }

    private static String extractJsonObject(String json, String key) {
        String pattern = "\"" + key + "\"\\s*:\\s*(\\{[^}]*\\})";
        java.util.regex.Pattern p = java.util.regex.Pattern.compile(pattern);
        java.util.regex.Matcher m = p.matcher(json);
        if (m.find()) {
            return m.group(1);
        }
        return null;
    }

    private static String extractJsonArray(String json, String key) {
        String pattern = "\"" + key + "\"\\s*:\\s*(\\[[^\\]]*\\])";
        java.util.regex.Pattern p = java.util.regex.Pattern.compile(pattern);
        java.util.regex.Matcher m = p.matcher(json);
        if (m.find()) {
            return m.group(1);
        }
        return null;
    }

    private static void printError(String message) {
        System.err.println(message);
    }

    static class ModuleInfo {
        String name;
        String module;
        String alias;
        String scope_tag;
        String version;
        String description;
        String author;
        String license;
        String source;
        String resolvedPath;
        String moduleHash;
        String scopeTable;
        Map<String, Object> exports = new LinkedHashMap<>();
        List<String> dependencies = new ArrayList<>();

        String toJson() {
            StringBuilder sb = new StringBuilder();
            sb.append("{");
            sb.append("\"name\":").append(escapeJson(name)).append(",");
            sb.append("\"module\":").append(escapeJson(module)).append(",");
            sb.append("\"alias\":").append(escapeJson(alias)).append(",");
            sb.append("\"scope_tag\":").append(escapeJson(scope_tag)).append(",");
            sb.append("\"version\":").append(escapeJson(version)).append(",");
            sb.append("\"description\":").append(escapeJson(description)).append(",");
            sb.append("\"author\":").append(escapeJson(author)).append(",");
            sb.append("\"license\":").append(escapeJson(license)).append(",");
            sb.append("\"exports\":{");
            boolean first = true;
            for (Map.Entry<String, Object> entry : exports.entrySet()) {
                if (!first) sb.append(",");
                sb.append("\"").append(entry.getKey()).append("\":");
                if (entry.getValue() instanceof List) {
                    sb.append(listToJson((List<?>) entry.getValue()));
                } else if (entry.getValue() instanceof Map) {
                    sb.append(mapToJson((Map<?, ?>) entry.getValue()));
                } else {
                    sb.append(escapeJson(String.valueOf(entry.getValue())));
                }
                first = false;
            }
            sb.append("},");
            sb.append("\"dependencies\":").append(listToJson(dependencies)).append(",");
            sb.append("\"source\":").append(escapeJson(source));
            sb.append("}");
            return sb.toString();
        }

        private String escapeJson(String value) {
            if (value == null) return "null";
            return "\"" + value.replace("\\", "\\\\")
                            .replace("\"", "\\\"")
                            .replace("\n", "\\n")
                            .replace("\r", "\\r")
                            .replace("\t", "\\t") + "\"";
        }

        private String listToJson(List<?> list) {
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) sb.append(",");
                Object item = list.get(i);
                if (item instanceof String) {
                    sb.append(escapeJson((String) item));
                } else {
                    sb.append(item);
                }
            }
            sb.append("]");
            return sb.toString();
        }

        private String mapToJson(Map<?, ?> map) {
            StringBuilder sb = new StringBuilder("{");
            boolean first = true;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!first) sb.append(",");
                sb.append(escapeJson(String.valueOf(entry.getKey())))
                  .append(":")
                  .append(escapeJson(String.valueOf(entry.getValue())));
                first = false;
            }
            sb.append("}");
            return sb.toString();
        }
    }
}
