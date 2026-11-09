/* Publishes the ACPI "backlight" device that AppleBacklight's AppleIntelPanelA matches.
   _UID 10 selects the F10 panel-table family in AppleBacklight's ApplePanels. */
DefinitionBlock ("", "SSDT", 2, "NC10", "PNLF", 0x00000000)
{
    Scope (\_SB)
    {
        Device (PNLF)
        {
            Name (_HID, EisaId ("APP0002"))
            Name (_CID, "backlight")
            Name (_UID, 0x0A)
            Name (_STA, 0x0B)
        }
    }
}
