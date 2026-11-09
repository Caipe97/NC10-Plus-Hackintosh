// Headless export: decompiled C and a function index for the current program.
import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import java.io.*;
public class ExportAll extends GhidraScript {
  @Override public void run() throws Exception {
    File dir = new File(getScriptArgs()[0]);
    String n = currentProgram.getName();
    DecompInterface d = new DecompInterface();
    d.openProgram(currentProgram);
    int ok = 0, bad = 0;
    try (PrintWriter c = new PrintWriter(new File(dir, n + ".c"));
         PrintWriter idx = new PrintWriter(new File(dir, n + ".funcs.txt"))) {
      for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
        idx.println(f.getEntryPoint() + " " + f.getBody().getNumAddresses() + " " + f.getName(true));
        if (f.isExternal() || f.isThunk()) continue;
        DecompileResults r = d.decompileFunction(f, 90, monitor);
        c.println("// ==== " + f.getEntryPoint() + " " + f.getName(true));
        if (r != null && r.decompileCompleted()) { c.println(r.getDecompiledFunction().getC()); ok++; }
        else { c.println("// decompile failed"); bad++; }
      }
    }
    d.dispose();
    println("EXPORT " + n + " ok=" + ok + " failed=" + bad);
  }
}
