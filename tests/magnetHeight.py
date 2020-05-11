from opentrons import protocol_api, types
import json

metadata =  {
    "protocolName": "RNA extraction protocol",
    "author": "Angel Menendez Vazquez <angel.menendez_vazquez@kcl.ac.uk>",
    "description": "Testing different magnet heights to see which ones are appropriate for our labware: Zymo, Starlab and Eppendorf",
    "apiLevel": "2.3"
}

def run(protocol: protocol_api.ProtocolContext):
    #Labware
        #Modules
    magneto = protocol.load_module("magdeck", 1)
        #Plates
    #Starlab = magneto.load_labware("usascientific_96_wellplate_2.4ml_deep", label = "Deep well") # E2896-1810 11.4mm
    Eppendorf = magneto.load_labware("eppendorf_96_deepwell_2ml", label = "Deep well") # 11.8 mm
    #Zymo = magneto.load_labware("zymoresearch_96_deepwell_2400ul", label = "Deep well") # 12.5mm

    #Mackerey Nagel 10mm
    tiprack2 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
        #Pippetes
    p300 = protocol.load_instrument( "p300_multi", "left", tip_racks=[tiprack2])

        #variables
    Height1=12.7
    Height2=13
    Height3=13.3
    #Commands

    protocol.comment("Engaging with %s mm " %Height1)
    magneto.engage(height=Height1)
    protocol.delay(seconds=20)
    protocol.comment("Disengaging")
    magneto.disengage()

    protocol.comment("\n\nEngaging with %s mm " %Height2)
    magneto.engage(height=Height2)
    protocol.delay(seconds=20)
    protocol.comment("Disengaging")
    magneto.disengage()

    protocol.comment("\n\nEngaging with %s mm " %Height3)
    magneto.engage(height=Height3)
    protocol.delay(seconds=20)
    protocol.comment("DISENGAGING, TURN THE THING PROTOCOL OFF.")
    magneto.disengage()

    protocol.delay(minutes=20)

    p300.transfer(500, Eppendorf["A1"], Eppendorf["A2"])
