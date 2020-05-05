from opentrons import protocol_api, types
import json

metadata =  {
    "protocolName": "RNA extraction v2",
    "author": "Angel Menendez Vazquez <angel.menendez_vazquez@kcl.ac.uk>",
    "description": "Protocol for RNA extraction on 48 samples based on a SOP for 'Viral RNA Extraction with Beckman RNAdvance' and this script https://github.com/Opentrons/covid19/blob/master/protocols/OMI_Clinical/StationB_Zymo_20200407/StationB-48samples-Zymo-20200407.py",
    "apiLevel": "2.3"
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware

        #Modules
    magneto = protocol.load_module("magdeck", 7)
        #Plates
    reagents = protocol.load_labware("nest_12_reservoir_15ml", 5, label="Reagents reservoir")
    waste = protocol.load_labware("nest_12_reservoir_15ml", 11, label="Liquid waste reservoir")
    deepPlate = magneto.load_labware("usascientific_96_wellplate_2.4ml_deep", label = "Deep well")
    empty = protocol.load_labware("empty", 10, label="nothing") #This custom labware is just a copy of usascientific_96_wellplate_2. I use it to move around the deck.
    outplate = protocol.load_labware("eppendorf96_skirted_150ul", 4, label = "Output plate")
        #Tips
    tiprack1 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tiprack2 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tiprack3 = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    tiprack6 = protocol.load_labware("opentrons_96_tiprack_300ul", 6)
    tiprack9 = protocol.load_labware("opentrons_96_tiprack_300ul", 9)
    tiprack8 = protocol.load_labware("opentrons_96_tiprack_300ul", 8)
        #Pipettes
    p300 = protocol.load_instrument( "p300_multi", "left")

        #Assigning relevant labware elements to variables to make it easier to understand.
    tips_addProteinase = [tiprack8['A'+str(i)] for i in range(1, 7)] #0.5 tipracks
    tips_addBeads = [tiprack8['A'+str(i)] for i in range(7, 13)] #1 tiprack
    tips_supernatantBeads = [tiprack9['A'+str(i)] for i in range(1, 7)] #1.5 tipracks
    tips_addWBE = [tiprack9['A'+str(i)] for i in range(7, 13)] #2 tipracks
    tips_supernatantWBE = [tiprack6['A'+str(i)] for i in range(1, 7)] #2.5 tipracks
    tips_addEthanol1 = [tiprack6['A'+str(i)] for i in range(7, 13)]#3 tipracks
    tips_supernatantEthanol1 = [tiprack3['A'+str(i)] for i in range(1, 7)] #3.5 tipracks
    tips_addEthanol2 =  [tiprack3['A'+str(i)] for i in range(7, 13)]#4 tipracks
    tips_supernatantEthanol2 = [tiprack2['A'+str(i)] for i in range(1, 7)] #4.5 tipracks
    tips_addWater = [tiprack2['A'+str(i)] for i in range(7, 13)]#5 tipracks
    tips_transfer =  [tiprack1['A'+str(i)] for i in range(1, 7)] #5.5 tipracks

    proteinase = reagents["A1"]
    beads = reagents["A2"]
    WBE = reagents["A3"]
    ethanol = reagents["A4"]
    water = reagents["A5"]

    columnID = ["A"+str(i) for i in range(1,12,2)] # This way, I can access the same cols in different samples.

    #General variables
    p300.flow_rate.aspirate = 50 #Flow rate in ul / second
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 300
    magnetHeight= 18 #Maybe change? Standard height for this plate is 14.94. In Github they use 13.7
    originalVol = 140
    proteinaseVol= 112
    beadsVol= 144
    initialSupernatant = originalVol + proteinaseVol + beadsVol
    washVol= 280
    dilutionVol= 80
    # izda= True # Deprecated. I used this to code the pipette offset when removing supernatant to move away of pellet. Unnecesary now, cause whe dont use whole plate.

    #Functions
    def remove_tip(ID):
        """For the sake of avoiding contamination, whenever I want to remove a tip that has been in contact with a sample
        I make it move to the back to an empty space (Pos 10), and from there to the trash"""
        p300.move_to(deepPlate[ID].top())
        p300.aspirate(20)
        p300.move_to(empty[ID].top())
        p300.drop_tip()

    def well_mix(loc, vol, reps, height=5.5):
        """Aspirates <vol> from bottom of well and dispenses it from 5.5 mm of height <reps> times"""
        loc1 = loc.bottom().move(types.Point(x=1, y=0, z=0.6))
        loc2 = loc.bottom().move(types.Point(x=1, y=0, z=height))
        p300.aspirate(20, loc1)
        for _ in range(reps-1):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc2)
        p300.dispense(20, loc2)

    def remove_supernatant(src, emptyCol, vol, dump, izda=True):
        """While <vol> is bigger than 180ul, it divides it in 180ul trips.
        Flow rate is in ul/second
        Positive X means to move to the right. With the wells we use (Column 1,3,5,7,9 and 11) pellet is placed to the right, so we use a small offset to the left"""
        p300.flow_rate.aspirate = 20
        tvol = vol
        side = 0
        #if (izda==False): # This is deprecated. Left here in case we want to do a 96 samples script
        #    side=2
        while tvol > 180:
            p300.aspirate(20, src.top() )
            p300.aspirate(180, src.bottom().move(types.Point(x=-1+side, y=0, z=0.5)))
            p300.move_to(emptyCol.top())
            p300.dispense(200, dump)
            protocol.delay(seconds=2)
            p300.blow_out() #When the pipette is empty, expel quite a lot of air all of a sudden
            p300.move_to(empty["A1"].top())
            tvol -= 180
        p300.aspirate(20, src.top() )
        p300.aspirate(tvol, src.bottom().move(types.Point(x=-1+side, y=0, z=0.5)))
        p300.move_to(emptyCol.top())
        p300.dispense(200, dump)
        protocol.delay(seconds=2)
        p300.blow_out()
        p300.flow_rate.aspirate = 50

    def slow_transfer(vol, src, to):
        """Similar to remove_supernatant, but the other way around. It transfers from point A to point B in 180ul trips and pours liquid
        from the top, to avoid contaminating the tip while transfering all the necessary volume"""
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

    #These next functions are more specific.

    def removing_step(vol, wasteID, columnID, tips, reagentName="Something"):
        """There are 4 steps of supernatant removal which are pretty much similar"""
        protocol.comment("Removing %s ul of supernatant (%s) while magnet is still engaged" % (vol, reagentName) )
        for ID, tip in zip(columnID, tips):
            p300.pick_up_tip(tip)
            remove_supernatant(src=deepPlate[ID], emptyCol=empty[ID], vol=vol, dump=waste[wasteID])
            remove_tip(ID)

    def adding_step(vol, reagent, reagentName, incubationTime, columnID, tips):
        """Same as before, but adding"""
        protocol.comment("Transfering %s ul of %s" % (vol, reagentName))
        for ID, tip in zip(columnID, tips):
            p300.pick_up_tip(tip)
            slow_transfer(vol, reagent, deepPlate[ID])
            well_mix(deepPlate[ID], 70, 5)
            remove_tip(ID)
        #Incubation
        protocol.comment("Engaging magnet and incubating for %s minutes" % incubationTime)
        magneto.engage(height=magnetHeight)
        protocol.delay(minutes=incubationTime)

    ##############################################################################################
    # C O M M A N D S || Hello, actual protocol!

        #STEP 1: Add Proteinase K/LBF. I don't use the adding_step function here because there are slight variations which I don't want to add to the function
    protocol.comment("Samples should have an initual volume of 140ul")
    protocol.comment("Adding %s ul of Proteinase K/LBF to samples" % proteinaseVol)
    for ID, tip in zip(columnID, tips_addProteinase):
        p300.pick_up_tip(tip)
        slow_transfer(proteinaseVol, proteinase, deepPlate[ID])
        well_mix(deepPlate[ID], 40, 5)
        remove_tip(ID)

        #INCUBATION 1: 10 min [Total: 10 min]
    protocol.comment("Incubating for 10 minutes")
    protocol.delay(minutes=10)

        #STEP 2: mix magnetic beads, add them to samples and mix sample well. No adding_step function for the same reasons as before.
    protocol.comment("Enough incubation, time to do s t u f f")
    iteration = 0
    for ID, tip in zip(columnID, tips_addBeads):
        p300.pick_up_tip(tip)
        if (iteration==0): #The first time, we mix the magnetic beads.
            protocol.comment("Mixing magnetic beads")
            well_mix(beads, 100, 5, height=30)
            p300.blow_out(beads.top())
            iteration = 2
        protocol.comment("Transfering %s ul from beads to col %s" % (beadsVol, ID))
        slow_transfer(beadsVol, beads, deepPlate[ID])
        well_mix(deepPlate[ID], 40, 5)
        remove_tip(ID)

        #INCUBATION 2: 5 min without magnet [Total: 15 min]
    protocol.comment("Incubating for 5 minutes")
    protocol.delay(minutes=5)
        #INCUBATION 3: 5 min incubation with magnet [Total: 20 min]
    protocol.comment("Starting magnet and incubating for 5 min")
    magneto.engage(height=magnetHeight)
    protocol.delay(minutes=5)

        #STEP 3: Remove magnetic beads supernatant
    protocol.comment("Removing %s ul of supernatant while magnet is still engaged" % initialSupernatant)
    removing_step(vol= initialSupernatant, wasteID="A1", reagentName="beads and proteinase",
    columnID=columnID, tips=tips_supernatantBeads)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 4: Add 280 ul of Wash WBE
    adding_step(vol= washVol, reagent=WBE, reagentName="WBE", incubationTime=3,
    columnID=columnID, tips=tips_addWBE)
        #INCUBATION 4: 3 min incubaton with magnet [Total: 23 min]


        #STEP 5: Removing WBE Supernatant
    removing_step(vol= washVol, wasteID="A2", reagentName="WBE",
    columnID=columnID, tips=tips_supernatantWBE)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 6: First wash with Ethanol
    adding_step(vol= washVol, reagent=ethanol, reagentName="Ethanol 70% (First time)", incubationTime=3,
    columnID=columnID, tips=tips_addEthanol1)
        #INCUBATION 5: 3 min incubaton with magnet [Total: 26 min]


        #STEP 7: Removing the supernatant of first wash with Ethanol
    removing_step(vol= washVol, wasteID="A3", reagentName="Ethanol 70% (First time)",
    columnID=columnID, tips=tips_supernatantEthanol1)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 8: Second wash with Ethanol
    adding_step(vol= washVol, reagent=ethanol, reagentName="Ethanol 70% (Second time)", incubationTime=3,
    columnID=columnID, tips=tips_addEthanol2)
        #INCUBATION 6: 3 min incubaton with magnet [Total: 26 min]


        #STEP 9: Removing the supernatant of second wash with Ethanol
    removing_step(vol=washVol, wasteID="A4", reagentName="Ethanol 70% (Second time)",
    columnID=columnID, tips=tips_supernatantEthanol2)

        #INCUBATION 7: 5 min incubaton with magnet [Total: 31 min]
    protocol.comment("This time, I do not disengage the magnet and let the beads dry for 5 min")
    protocol.delay(minutes=5)

        #STEP 10: Diluting samples in 80 ul of RNAse free water
    protocol.comment("Disengaging magnet")
    magneto.disengage()
    protocol.comment("Diluting samples in %s ul of RNAse free water" % dilutionVol)
    adding_step(vol= dilutionVol, reagent=water, reagentName="RNAse-free water",incubationTime=1,
    columnID=columnID, tips=tips_addWater)
        #INCUBATION 7: 1 min incubaton with magnet [Total: 32 min]

        #STEP 11: Transfering samples to output eppendorf 96 well plate
    protocol.comment("Transfering DNA to output plate")
    magneto.disengage()
    for ID, tip in zip(columnID, tips_transfer):
        p300.pick_up_tip(tip)
        slow_transfer(dilutionVol, deepPlate[ID], outplate[ID])
        remove_tip(ID)

    protocol.comment("Hecho!")
