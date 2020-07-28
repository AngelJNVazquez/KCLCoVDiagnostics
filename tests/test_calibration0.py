from opentrons import protocol_api, types
import json
import math

metadata =  {
    "protocolName": "Beckman RNA extraction protocol",
    "author": "Angel Menendez Vazquez <angel.menendez_vazquez@kcl.ac.uk>",
    "description": "Testing some relevant positions",
    "apiLevel": "2.3"
}

def run(protocol: protocol_api.ProtocolContext):

    ################### SETTING UP ###################
    ##                                              ##
    ##     ヽ༼ຈل͜ຈ༽ﾉ LABWARE ヽ༼ຈل͜ຈ༽ﾉ               ##
    ##                                              ##
    ##################################################

                # Positions are:
                # 10    11      TRASH
                # 7     8       9
                # 4     5       6
                # 1     2       3

        #Modules, plate and MAGNET HEIGHT
    magneto = protocol.load_module("magneticModuleV2", 6)
    deepPlate = magneto.load_labware("eppendorf_96_deepwell_2ml", label = "Deep well")
    magnetHeight= 5
    #########################################################################################################
    ##  We have tested appropriate height on GEN1 magdeck for different plates, these are the chosen ones  ##
    ##                                                                                                     ##
    ##  Zymoresearch - "zymoresearch_96_deepwell_2.4ml" - 12.5mm                                           ##
    ##  Eppendorf - "eppendorf_96_deepwell_2ml" - 11.8 mm                                                  ##
    ##  Starlab - "usascientific_96_wellplate_2.4ml_deep" - E2896-1810 11.4mm                              ##
    ##  Macherey-Nagel - - 10mm                                                                            ##
    #########################################################################################################

        #Plates
    reagents = protocol.load_labware("nest_12_reservoir_15ml", 5, label="Reagents reservoir")
    waste = protocol.load_labware("nest_12_reservoir_15ml", 9, label="Liquid waste reservoir")
    outplate = protocol.load_labware("eppendorf96_skirted_150ul", 3, label = "Output plate")
        #Tips - Ordered in the way they are used
    tiprack2 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    p300 = protocol.load_instrument( "p300_multi_gen2", "left", [tiprack2])

    bottomHeight = 0.5
    bottomMixHeight = 1
    generalHeight = 5
    topOffset= -5
    moveSide = 0

    def getMixingTopHeight(stringLabware, volume):
        labwareDefinition = protocol_api.labware.get_all_labware_definitions()
        for thing in labwareDefinition:
            protocol.comment(thing)

    def well_mix(vol, loc, reps, labwareName="eppendorf_96_deepwell_2ml", height=generalHeight, moveSide=0, bottomHeight = bottomMixHeight):
        """
        Aspirates <vol> from bottom of well and dispenses it from <height> <reps> times
        loc1 is a position at 0.3mm over the bottom of the well
        loc2 is a position in the same x and y posiiton than loc1, but at <height>mm over the bottom of the well
        The idea here is to take liquid to the very bottom and pour it from a higher point, to mix things
        """
        p300.flow_rate.aspirate = 100
        p300.flow_rate.dispense = 300
        getMixingTopHeight(labwareName, vol)
        loc1 = loc.bottom().move(types.Point(x=0+moveSide, y=0, z=bottomHeight))
        loc2 = loc.bottom().move(types.Point(x=0+moveSide, y=0, z=height))
        for _ in range(reps):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc1)
        p300.flow_rate.aspirate = 50
        p300.flow_rate.dispense = 150
        p300.dispense(20, loc.top(topOffset))

    p300.pick_up_tip(tiprack2["D1"])
    well_mix(100, deepPlate["A1"], 10, labwareName="eppendorf_96_deepwell_2ml", moveSide=1, bottomHeight=0.8)

    magneto.disengage()
    #p300.pick_up_tip(tiprack2["D1"].top().move(types.Point(x=0, y=-36, z=0)))
    protocol.delay(seconds=20)
    p300.move_to( reagents["A1"].bottom().move(types.Point(x=0, y=0, z=bottomHeight)) )
    protocol.delay(seconds=10)
    p300.move_to(deepPlate["A1"].bottom().move(types.Point(x=1, y=0, z=bottomMixHeight)) )
    protocol.delay(seconds=5)

    p300.move_to(outplate["A1"].bottom().move(types.Point(x=0, y=0, z=5)) )
    protocol.delay(seconds=10)
    p300.move_to(deepPlate["A1"].bottom().move(types.Point(x=-1, y=0, z=bottomHeight)) )
    protocol.delay(seconds=5)
    well_mix(100, deepPlate["A1"], 10, moveSide=-1)
    p300.return_tip()
    magneto.disengage()
    protocol.delay(minutes=10)

    p300.transfer(500, outplate["A1"], outplate["A2"])
    p300.transfer(500, reagents["A1"], reagents["A2"])
