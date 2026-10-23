// Java | FocusedDecompile.java | Ghidra 12.1.4/JDK 21 | static private-database analysis of two pinned PE functions.
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;
import com.google.gson.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;

public class FocusedDecompile extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) throw new IllegalArgumentException("plan JSON and output JSON required");
        JsonObject plan = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        String expected = plan.get("sample_sha256").getAsString();
        if (!expected.equalsIgnoreCase(currentProgram.getExecutableSHA256()))
            throw new IllegalStateException("Imported executable SHA-256 mismatch");
        if (!toAddr(plan.get("image_base").getAsString()).equals(currentProgram.getImageBase()))
            throw new IllegalStateException("Image base differs from the evidence plan");
        JsonObject result = new JsonObject();
        result.addProperty("sample_sha256", currentProgram.getExecutableSHA256());
        result.addProperty("method", "Ghidra 12.1.4 direct headless -noanalysis; bodies seeded from prior CFG, not REA provider Evidence");
        result.addProperty("target_executed", false);
        JsonArray output = new JsonArray();
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true); decompiler.toggleSyntaxTree(false);
        if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException(decompiler.getLastMessage());
        try {
            for (JsonElement value : plan.getAsJsonArray("functions")) {
                JsonObject item = value.getAsJsonObject();
                Address entry = toAddr(item.get("entry_va").getAsString());
                AddressSet body = new AddressSet();
                for (JsonElement range : item.getAsJsonArray("ranges")) {
                    JsonArray pair = range.getAsJsonArray();
                    body.addRange(toAddr(pair.get(0).getAsString()), toAddr(pair.get(1).getAsString()));
                }
                int checked = 0;
                for (JsonElement instruction : item.getAsJsonArray("instructions")) {
                    JsonObject row = instruction.getAsJsonObject();
                    byte[] bytes = HexFormat.of().parseHex(row.get("bytes").getAsString().replace(" ", ""));
                    byte[] loaded = getBytes(toAddr(row.get("address").getAsString()), bytes.length);
                    if (!java.util.Arrays.equals(loaded, bytes)) throw new IllegalStateException("Loaded code mismatch");
                    checked++;
                }
                DisassembleCommand command = new DisassembleCommand(entry, body, true);
                if (!command.applyTo(currentProgram, monitor)) throw new IllegalStateException(command.getStatusMsg());
                Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
                if (function == null) function = currentProgram.getFunctionManager().createFunction(item.get("label").getAsString(), entry, body, SourceType.USER_DEFINED);
                else function.setBody(body);
                DecompileResults decompiled = decompiler.decompileFunction(function, 60, monitor);
                JsonObject row = new JsonObject();
                row.addProperty("entry_va", entry.toString());
                row.addProperty("label", item.get("label").getAsString());
                row.addProperty("verified_instruction_records", checked);
                row.addProperty("completed", decompiled.decompileCompleted());
                row.addProperty("diagnostic", decompiled.getErrorMessage());
                if (decompiled.decompileCompleted()) row.addProperty("c", decompiled.getDecompiledFunction().getC());
                output.add(row); println("FOCUSED_RESULT " + entry + " " + decompiled.decompileCompleted());
            }
        } finally { decompiler.dispose(); }
        result.add("functions", output);
        Files.writeString(Path.of(args[1]), new GsonBuilder().setPrettyPrinting().create().toJson(result), StandardCharsets.UTF_8);
    }
}
