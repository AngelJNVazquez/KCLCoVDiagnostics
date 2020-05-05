from opentrons import protocol_api, types
import json

metadata =  {
    "protocolName": "RNA extraction v1",
    "author": "Angel Menendez Vazquez <angel.menendez_vazquez@kcl.ac.uk>",
    "description": "Protocol for RNA extraction based on a SOP for 'Viral RNA Extraction with Beckman RNAdvance' and this script https://github.com/Opentrons/covid19/blob/master/protocols/OMI_Clinical/StationB_Zymo_20200407/StationB-48samples-Zymo-20200407.py",
    "apiLevel": "2.2"
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware

        #Modules
    magneto = protocol.load_module("magdeck", 7)
        #Plates
    reagents = protocol.load_labware("nest_12_reservoir_15ml", 5, label="Reagents reservoir")
    waste = protocol.load_labware("nest_12_reservoir_15ml", 11, label="Liquid waste reservoir")
    deepPlate = magneto.load_labware("usascientific_96_wellplate_2.4ml_deep", label = "Deep well")
    empty = protocol.load_labware("empty", 10, label="nothing")
    outplate = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", 4, label = "Output plate")
        #Tips
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
        # Pipettes
    p300 = protocol.load_instrument( "p300_multi", "left", tip_racks=[tiprack] )

    #Variables
    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 300
    magnetHeight= 18
    beadsVol= 144
    washVol= 280
    izda= True

    #Functions
    def well_mix(loc, vol, reps):
        loc1 = loc.bottom().move(types.Point(x=1, y=0, z=0.6))
        loc2 = loc.bottom().move(types.Point(x=1, y=0, z=5.5))
        p300.aspirate(20, loc1)
        for _ in range(reps-1):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc2)
        p300.dispense(20, loc2)

    def remove_supernatant(src, vol, dump, izda=True):
        p300.flow_rate.aspirate = 20
        tvol = vol
        side = 2
        if (izda==True):
            side=0
        while tvol > 180:
            p300.aspirate(20, src.top() )
            p300.aspirate(180, src.bottom().move(types.Point(x=-1+side, y=0, z=0.5)))
            p300.move_to(empty["A1"].top())
            p300.dispense(200, dump)
            protocol.delay(seconds=2)
            p300.blow_out()
            p300.move_to(empty["A1"].top())
            tvol -= 180
        p300.aspirate(20, src.top() )
        p300.aspirate(tvol, src.bottom().move(types.Point(x=-1+side, y=0, z=0.5)))
        p300.move_to(empty["A1"].top())
        p300.dispense(200, dump)
        protocol.delay(seconds=2)
        p300.blow_out()
        p300.flow_rate.aspirate = 50

    def slow_transfer(vol, src, to):
        tvol = vol
        while tvol > 180:
            p300.aspirate(20, src.top() )
            p300.transfer(180, src.bottom().move(types.Point(x=-1, y=0, z=0.5)), to.top(-5), new_tip="never")
            protocol.delay(seconds=2)
            p300.dispense(20)
            tvol -= 180
        p300.aspirate(20, src.top() )
        p300.transfer(tvol,src.bottom().move(types.Point(x=-1, y=0, z=0.5)), to.top(-5), new_tip="never")
        protocol.delay(seconds=2)
        p300.dispense(20)

    # Commands
        #STEP1: Add solution to each sample and mix.
    protocol.comment("Adding bead solution to samples and mixing")
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        slow_transfer(144, reagents["A1"], column)
        well_mix(column, 40, 5)
        p300.move_to(column.top())
        p300.aspirate(20)
        p300.move_to(empty["A1"].top())
        p300.drop_tip()
    tiprack.reset()

        #STEP 2: Incubation
    protocol.comment("Incubating for 5 minutes")
    protocol.delay(minutes=5)

        #STEP 3: Incubation with magnet
    protocol.comment("Starting magnet and incubating for 5 min")
    magneto.engage(height=magnetHeight)
    protocol.delay(minutes=5)

        #STEP 4: Remove supernatant
    protocol.comment("Removing supernatant while magnet is still engaged")
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        remove_supernatant(column, 256, waste["A1"],izda)
        p300.drop_tip()
        if (izda==True):
            izda=False
        else:
            izda=True
    tiprack.reset()

        #STEP 5: Add 280 ul of Wash WBE
    protocol.comment("Disengaging magnet, transfering Wash WBE and incubating with magnet 3 min")
    magneto.disengage()
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        slow_transfer(280, reagents["A2"], column)
        well_mix(column, 70, 5)
        p300.move_to(column.top())
        p300.aspirate(20)
        p300.move_to(empty["A1"].top())
        p300.drop_tip()
    magneto.engage(height=magnetHeight)
    protocol.delay(minutes=3)
    tiprack.reset()

    protocol.comment("Removing supernatant (Wash WBE) while magnet is still engaged")
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        remove_supernatant(column, 280, waste["A2"],izda)
        p300.drop_tip()
        if (izda==True):
            izda=False
        else:
            izda=True
    tiprack.reset()

    #STEP WW:
    protocol.comment("Disengaging magnet, transfering ethanol 70% and incubating with magnet 3 min (First time)")
    magneto.disengage()
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        slow_transfer(280, reagents["A3"], column)
        well_mix(column, 70, 5)
        p300.move_to(column.top())
        p300.aspirate(20)
        p300.move_to(empty["A1"].top())
        p300.drop_tip()
    magneto.engage(height=magnetHeight)
    protocol.delay(minutes=3)
    tiprack.reset()

    protocol.comment("Removing supernatant (first EtOH) while magnet is still engaged")
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        remove_supernatant(column, 280, waste["A3"],izda)
        p300.drop_tip()
        if (izda==True):
            izda=False
        else:
            izda=True
    tiprack.reset()

        #STEP WW:
    protocol.comment("Same, but with ethanol (Second time)")
    magneto.disengage()
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        slow_transfer(280, reagents["A3"], column)
        well_mix(column, 70, 5)
        p300.move_to(column.top())
        p300.aspirate(20)
        p300.move_to(empty["A1"].top())
        p300.drop_tip()
    magneto.engage(height=magnetHeight)
    protocol.delay(minutes=2)
    tiprack.reset()

    protocol.comment("Removing supernatant (Second EtOH) while magnet is still engaged")
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        remove_supernatant(column, 280, waste["A4"],izda)
        p300.drop_tip()
        if (izda==True):
            izda=False
        else:
            izda=True
    tiprack.reset()

    protocol.comment("Now allowing beads to air dry for five minutes")
    protocol.delay(minutes=5)

    protocol.comment("Disengaging magnet and eluding in 80 ul of RNAse free water")
    magneto.disengage()
    for column in deepPlate.rows()[0]:
        p300.pick_up_tip()
        slow_transfer(80, reagents["A4"], column)
        well_mix(column, 70, 5)
        p300.move_to(column.top())
        p300.aspirate(20)
        p300.move_to(empty["A1"].top())
        p300.drop_tip()
    magneto.engage(height=magnetHeight)
    protocol.delay(minutes=1)
    tiprack.reset()

    protocol.comment("Transfering DNA to output plate")
    magneto.disengage()
    for inputCol,outputCol in zip(deepPlate.rows()[0], outplate.rows()[0]):
        p300.pick_up_tip()
        slow_transfer(80, inputCol, outputCol)
        p300.move_to(inputCol.top())
        p300.aspirate(20)
        p300.move_to(empty["A1"].top())
        p300.drop_tip()
    tiprack.reset()
