/* Answers every OS query from the DSDT as Windows 7 would, so the firmware sees the same OS type as under
   Linux and Windows 7 (OSTB/TPOS 0x20, OSYS 0x07D9). Needs an OpenCore ACPI patch renaming the DSDT's _OSI to XOSI.
   Every _OSI string in this DSDT is a Windows one, so all are answered true. */
DefinitionBlock ("", "SSDT", 2, "NC10", "XOSI", 0x00000001)
{
    Method (XOSI, 1, NotSerialized)
    {
        Return (Ones)
    }
}
