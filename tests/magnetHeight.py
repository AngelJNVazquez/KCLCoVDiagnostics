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
        #Plates
    #Starlab = magneto.load_labware("usascientific_96_wellplate_2.4ml_deep", label = "Deep well") # E2896-1810 11.4mm
    Eppendorf = protocol.load_labware("eppendorf_96_deepwell_2ml", 6, label = "Deep well") # 11.8 mm
    #Zymo = magneto.load_labware("zymoresearch_96_deepwell_2400ul", label = "Deep well") # 12.5mm

    #Mackerey Nagel 10mm
    tiprack2 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
        #Pippetes
    p300 = protocol.load_instrument( "p300_multi_gen2", "left", tip_racks=[tiprack2])

        #variables
    Height1=12.7
    Height2=13
    Height3=13.3
    #Commands

    protocol.delay(minutes=20)

    p300.transfer(500, Eppendorf["A1"], Eppendorf["A2"])
