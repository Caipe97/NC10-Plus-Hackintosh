#!/usr/bin/python
"""NC10 Plus post-install. Run on the netbook, in Mac OS X 10.6.0, after booting the unaccelerated EFI.

Takes the stock kexts already on this Mac, patches them, puts the GPU and PS/2 drivers on the OpenCore EFI
partition, switches that EFI to its full config, installs the patched audio driver and rebuilds the kext caches.
Originals are kept in /Library/Backups/nc10-stock-kexts.

Written for the Python 2.6 that ships with 10.6.

usage: sudo python install.py [--mode full|gpu] [--list-efi] [--yes]
       python install.py --build-only DIR      build just the two GPU kexts, for use with your own OpenCore
Testing without touching the system: python install.py --root DIR --efi DIR --yes
"""
import hashlib
import json
import optparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PATCHES = os.path.join(os.path.dirname(HERE), "patches")
SUMS = json.load(open(os.path.join(PATCHES, "checksums.json")))

GMA, FB, HDA = "AppleIntelGMA950.kext", "AppleIntelIntegratedFramebuffer.kext", "AppleHDA.kext"
GMA_BIN = "Contents/MacOS/AppleIntelGMA950"
FB_BIN = "AppleIntelIntegratedFramebuffer"
HDA_BIN = "Contents/MacOS/AppleHDA"
TP = "VoodooPS2Controller.kext/Contents/PlugIns/VoodooPS2Trackpad.kext"
TP_BIN = "Contents/MacOS/VoodooPS2Trackpad"
PS2 = "VoodooPS2Controller.kext"
FULL_CONFIG = "EFI/OC/config.full.plist"
CONFIGS = {"full": "config.full.plist", "gpu": "config.gpu.plist"}


def die(msg):
    sys.stderr.write("\nStopped: %s\nNothing further was changed.\n" % msg)
    sys.exit(1)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def run(cmd, env=None):
    """Run a command and return its output, stopping on failure."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    out = p.communicate()[0]
    if p.returncode != 0:
        die("%s failed:\n%s" % (" ".join(cmd), out))
    return out


def copy_tree(src, dst):
    """cp, not shutil: FAT cannot hold the metadata shutil tries to copy. COPYFILE_DISABLE avoids ._ files.
    -L because FAT has no symlinks, and Apple's kexts link into _CodeSignature."""
    env = dict(os.environ, COPYFILE_DISABLE="1")
    run(["/bin/cp", "-RL", src, dst], env)


def patch(script, src, dst):
    run([sys.executable, os.path.join(PATCHES, script), src, dst])


def edit(path, change):
    f = open(path)
    text = f.read()
    f.close()
    text = change(text)
    f = open(path, "w")
    f.write(text)
    f.close()


def sub1(pattern, repl, text):
    new, n = re.subn(pattern, repl, text)
    if n != 1:
        die("unexpected Info.plist contents (%s)" % pattern)
    return new


def gpu_plist(boot_required):
    def change(text):
        text = sub1(r"0x27A28086</string>", "0x27A28086 0xA0118086</string>", text)
        text = sub1(r"(<key>CFBundleVersion</key>\s*<string>)6\.0\.0(</string>)", r"\g<1>6.0.1\2", text)
        if boot_required:
            head, tail = text.rsplit("</dict>", 1)
            text = head + "\t<key>OSBundleRequired</key>\n\t<string>Root</string>\n</dict>" + tail
        return text
    return change


def find_stock(name, binary, table_key, ext, backup):
    """The stock kext is in Extensions on a first run and in the backup folder on a re-run."""
    for folder in (ext, backup):
        path = os.path.join(folder, name)
        if os.path.isfile(os.path.join(path, binary)) and sha(os.path.join(path, binary)) == SUMS["stock"][table_key]:
            return path
    die("no stock %s from build 10A432 found in %s or %s" % (name, ext, backup))


def build(ext, backup, efi, work, mode):
    """Everything is prepared in a temporary folder before anything on the system changes."""
    kexts = os.path.join(work, "Kexts")
    os.mkdir(kexts)

    src = find_stock(GMA, GMA_BIN, "AppleIntelGMA950", ext, backup)
    copy_tree(src, os.path.join(kexts, GMA))
    shutil.rmtree(os.path.join(kexts, GMA, "Contents/_CodeSignature"), True)
    patch("patch_gma.py", os.path.join(src, GMA_BIN), os.path.join(kexts, GMA, GMA_BIN))
    edit(os.path.join(kexts, GMA, "Contents/Info.plist"), gpu_plist(True))

    src = find_stock(FB, FB_BIN, "AppleIntelIntegratedFramebuffer", ext, backup)
    copy_tree(src, os.path.join(kexts, FB))
    shutil.rmtree(os.path.join(kexts, FB, "Contents/_CodeSignature"), True)
    patch("patch_fb.py", os.path.join(src, FB_BIN), os.path.join(kexts, FB, FB_BIN))
    edit(os.path.join(kexts, FB, "Info.plist"), gpu_plist(False))

    checks = [("AppleIntelGMA950", os.path.join(kexts, GMA, GMA_BIN)),
              ("AppleIntelIntegratedFramebuffer", os.path.join(kexts, FB, FB_BIN))]
    hda = None
    if mode == "full":
        # The PS/2 drivers ship unpatched on the EFI partition. On a re-run the trackpad is already patched.
        source = os.path.join(efi, "EFI/OC/Kexts", PS2)
        if not os.path.isdir(source):
            die("%s is missing from the EFI partition" % PS2)
        copy_tree(source, os.path.join(kexts, PS2))
        trackpad = os.path.join(kexts, TP)
        binary = os.path.join(trackpad, TP_BIN)
        if sha(binary) == SUMS["stock"]["VoodooPS2Trackpad"]:
            patch("patch_trackpad.py", binary, binary + ".new")
            os.rename(binary + ".new", binary)
            edit(os.path.join(trackpad, "Contents/Info.plist"), lambda t: sub1(
                r"(<key>MultiFingerWLimit</key>\s*<integer>)9(</integer>)", r"\g<1>6\2", t))
        checks.append(("VoodooPS2Trackpad", binary))

        if not hda_done(ext):
            src = find_stock(HDA, HDA_BIN, "AppleHDA", ext, backup)
            hda = os.path.join(work, "AppleHDA")
            patch("patch_hda.py", os.path.join(src, HDA_BIN), hda)
            checks.append(("AppleHDA", hda))

    for name, path in checks:
        if sha(path) != SUMS["patched"][name]:
            die("patched %s has an unexpected checksum" % name)
        print("  verified %s" % name)
    return kexts, hda


def hda_done(ext):
    path = os.path.join(ext, HDA, HDA_BIN)
    return os.path.isfile(path) and sha(path) == SUMS["patched"]["AppleHDA"]


def mounted_at(dev):
    for line in run(["/sbin/mount"]).splitlines():
        m = re.match(r"%s on (.*) \(" % re.escape(dev), line)
        if m:
            return m.group(1)
    return None


def scan_efi():
    """Mount each FAT or EFI partition and return those holding this repository's EFI: [(dev, mountpoint, ours)]."""
    found = []
    for dev in re.findall(r"^\s+\d+:\s+(?:EFI|DOS_FAT_\d+|Microsoft Basic Data)\b.*?(disk\d+s\d+)\s*$",
                          run(["/usr/sbin/diskutil", "list"]), re.M):
        node = "/dev/" + dev
        point, ours = mounted_at(node), False
        if not point:
            point, ours = "/Volumes/nc10-" + dev, True
            if not os.path.isdir(point):
                os.mkdir(point)
            if subprocess.call(["/sbin/mount", "-t", "msdos", node, point]) != 0:
                os.rmdir(point)
                continue
        if os.path.isfile(os.path.join(point, "EFI/OC/OpenCore.efi")):
            found.append((dev, point, ours))
        elif ours:
            release(point)
    return found


def release(point):
    subprocess.call(["/sbin/umount", point])
    if point.startswith("/Volumes/nc10-") and os.path.isdir(point):
        os.rmdir(point)


def choose_efi(found, assume_yes):
    usable = [f for f in found if os.path.isfile(os.path.join(f[1], FULL_CONFIG))]
    if not usable:
        die("no OpenCore EFI containing %s was found. Is the USB drive plugged in?" % FULL_CONFIG)
    if len(usable) == 1:
        return usable[0]
    if assume_yes:
        die("more than one EFI partition found, run without --yes to choose")
    for i, f in enumerate(usable):
        print("  %d) %s" % (i + 1, f[0]))
    answer = raw_input("Which one did you boot from? ").strip()
    if not answer.isdigit() or not 1 <= int(answer) <= len(usable):
        die("no valid choice")
    return usable[int(answer) - 1]


def apply_changes(kexts, hda, efi, ext, backup, real, mode):
    oc = os.path.join(efi, "EFI/OC")

    print("Updating the EFI partition")
    if not os.path.exists(os.path.join(oc, "config.plist.before-postinstall")):
        shutil.copyfile(os.path.join(oc, "config.plist"), os.path.join(oc, "config.plist.before-postinstall"))
    for name in os.listdir(kexts):
        target = os.path.join(oc, "Kexts", name)
        if os.path.exists(target):
            shutil.rmtree(target)
        copy_tree(os.path.join(kexts, name), target)
    shutil.copyfile(os.path.join(oc, CONFIGS[mode]), os.path.join(oc, "config.plist"))

    print("Saving the stock drivers to %s" % backup)
    if not os.path.isdir(backup):
        os.makedirs(backup)
    for name in (GMA, FB):
        here = os.path.join(ext, name)
        if os.path.isdir(here):
            if os.path.exists(os.path.join(backup, name)):
                shutil.rmtree(here)
            else:
                os.rename(here, os.path.join(backup, name))
    if hda:
        if not os.path.exists(os.path.join(backup, HDA)):
            run(["/bin/cp", "-Rp", os.path.join(ext, HDA), backup])
        target = os.path.join(ext, HDA, HDA_BIN)
        shutil.copyfile(hda, target)
        os.chmod(target, 493)  # 0755
        if real:
            os.chown(target, 0, 0)

    if real:
        print("Rebuilding the kext caches, this takes a few minutes")
        run(["/usr/bin/touch", ext])
        if mode == "full":
            # The prelinked cache only takes kexts loaded this session, and AppleALC needs AppleHDA to be in it.
            subprocess.call(["/sbin/kextload", os.path.join(ext, HDA)])
            if "com.apple.driver.AppleHDA " not in run(["/usr/sbin/kextstat"]):
                print("Warning: AppleHDA did not load. If there is no sound after restarting, run this script again.")
        run(["/usr/sbin/kextcache", "-system-prelinked-kernel"])
        run(["/usr/sbin/kextcache", "-system-mkext"])
        run(["/usr/bin/pmset", "-a", "hibernatemode", "0"])
        run(["/bin/sync"])


def choose_mode(o):
    if o.mode:
        return o.mode
    if o.yes:
        die("--yes needs --mode full or --mode gpu")
    print("\nWhat do you want to install?")
    print("  1) Everything: graphics acceleration, audio and the touchpad fixes")
    print("  2) Graphics acceleration only")
    answer = raw_input("Choose 1 or 2: ").strip()
    if answer not in ("1", "2"):
        die("no valid choice")
    return {"1": "full", "2": "gpu"}[answer]


def main():
    ap = optparse.OptionParser(usage=__doc__)
    ap.add_option("--mode", choices=["full", "gpu"], help="full: everything, gpu: graphics only")
    ap.add_option("--build-only", metavar="DIR", help="only write the two patched GPU kexts to DIR")
    ap.add_option("--list-efi", action="store_true", help="show the OpenCore partitions found, change nothing")
    ap.add_option("--yes", action="store_true", help="do not ask for confirmation")
    ap.add_option("--root", help="testing: use this folder instead of the system disk")
    ap.add_option("--efi", help="testing: use this folder as the EFI partition")
    o = ap.parse_args()[0]

    real = not o.root
    if real and not o.build_only and os.geteuid() != 0:
        die("run this with sudo")
    build_id = run(["/usr/bin/sw_vers", "-buildVersion"]).strip()
    if build_id != "10A432":
        die("this needs Mac OS X 10.6.0 build 10A432, this Mac has %s" % build_id)

    root = o.root or "/"
    ext = os.path.join(root, "System/Library/Extensions")
    backup = os.path.join(root, "Library/Backups/nc10-stock-kexts")

    if o.build_only:
        work = tempfile.mkdtemp(prefix="nc10-")
        try:
            kexts = build(ext, backup, None, work, "gpu")[0]
            if not os.path.isdir(o.build_only):
                os.makedirs(o.build_only)
            for name in (GMA, FB):
                copy_tree(os.path.join(kexts, name), os.path.join(o.build_only, name))
        finally:
            shutil.rmtree(work, True)
        print("\nWrote %s and %s to %s. See \"Using your own OpenCore\" in docs/INSTALL.md." % (GMA, FB, o.build_only))
        return

    found = []
    try:
        if o.efi:
            efi, dev = o.efi, "test folder"
        else:
            found = scan_efi()
            if o.list_efi:
                for f in found:
                    print("%s  %s  full config: %s" % (f[0], f[1], os.path.isfile(os.path.join(f[1], FULL_CONFIG))))
                return
            dev, efi = choose_efi(found, o.yes)[:2]

        mode = choose_mode(o)
        if not os.path.isfile(os.path.join(efi, "EFI/OC", CONFIGS[mode])):
            die("%s is missing from the EFI partition" % CONFIGS[mode])

        work = tempfile.mkdtemp(prefix="nc10-")
        try:
            print("Patching your stock drivers")
            kexts, hda = build(ext, backup, efi, work, mode)
            print("\nThis will:")
            print("  - add the patched %s to the EFI partition on %s" % (
                mode == "full" and "graphics and touchpad drivers" or "graphics drivers", dev))
            print("  - switch that EFI to %s" % CONFIGS[mode])
            print("  - move the stock graphics drivers to %s" % backup)
            if mode == "full":
                print("  - install the patched AppleHDA")
            print("  - rebuild the kext caches")
            if not o.yes and raw_input("\nType yes to continue: ").strip() != "yes":
                die("cancelled")
            apply_changes(kexts, hda, efi, ext, backup, real, mode)
        finally:
            shutil.rmtree(work, True)
        print("\nDone. Restart and boot from the same OpenCore drive.")
    finally:
        for f in found:
            if f[2]:
                release(f[1])


if __name__ == "__main__":
    main()
