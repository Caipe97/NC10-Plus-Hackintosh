/* Makes _WAK return the package the ACPI spec requires. Needs an OpenCore patch renaming the DSDT's _WAK to XWAK.
   Build: iasl, then tools/aml_strip_externals.py (10.6's interpreter rejects the External block). */
DefinitionBlock ("", "SSDT", 2, "NC10", "WAKFIX", 0x00000001)
{
    External (XWAK, MethodObj)

    Method (_WAK, 1, NotSerialized)
    {
        XWAK (Arg0)
        Return (Package (0x02) { 0x00, 0x00 })
    }
}
