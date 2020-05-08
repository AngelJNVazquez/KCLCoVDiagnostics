from opentrons import protocol_api, types
import json

metadata =  {
    "protocolName": "RNA extraction protocol",
    "author": "Angel Menendez Vazquez <angel.menendez_vazquez@kcl.ac.uk>",
    "description": "Protocol for RNA extraction on 48 samples based on a SOP for 'Viral RNA Extraction with Beckman RNAdvance' and this script https://github.com/Opentrons/covid19/blob/master/protocols/OMI_Clinical/StationB_Zymo_20200407/StationB-48samples-Zymo-20200407.py",
    "apiLevel": "2.2"
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    # Positions are:
    # 10    11      TRASH
    # 7     8       9
    # 4     5       6
    # 1     2       3

        #Modules
    magneto = protocol.load_module("magdeck", 6)
        #Plates
    reagents = protocol.load_labware("nest_12_reservoir_15ml", 5, label="Reagents reservoir")
    waste = protocol.load_labware("nest_12_reservoir_15ml", 9, label="Liquid waste reservoir")
    deepPlate = magneto.load_labware("usascientific_96_wellplate_2.4ml_deep", label = "Deep well")
    outplate = protocol.load_labware("eppendorf96_skirted_150ul", 3, label = "Output plate")
        #Tips - Ordered in the way they are taken
    tiprack2 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tiprack1 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tiprack4 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tiprack7 = protocol.load_labware("opentrons_96_tiprack_300ul", 7)
    tiprack8 = protocol.load_labware("opentrons_96_tiprack_300ul", 8)
    tiprack10 = protocol.load_labware("opentrons_96_tiprack_300ul", 10)

    tipracks = [tiprack10, tiprack8, tiprack7, tiprack4, tiprack1, tiprack2]
    availableTips = []
    for rack in tipracks:
        for i in range(1,13):
            availableTips.append(rack["A"+str(i)]) #Now, if I use availableTips.pop(), I dont have to assign a million variables to each tip.
        #Pipettes
    p300 = protocol.load_instrument( "p300_multi", "left")

        #Assigning relevant labware elements to variables to make it easier to understand.
    proteinase = reagents["A1"]
    beads = reagents["A2"]
    WBE = reagents["A3"]
    ethanol = reagents["A4"]
    water = reagents["A5"]

    columnID = ["A"+str(i) for i in range(1,12,2)] # Making it easier to access the column we will use.

    #General variables
        #Run variables
    runColumns=1 # Range 1-6. Samples should be a multiple of 8, or you will waste reagents.
    columnID = columnID[:runColumns]
        #Robot variables
    p300.flow_rate.aspirate = 50 #Flow rate in ul / second
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 300
    magnetHeight= 12.7 #In mm. We tested this height. Heights over this, move the Zymo plate upwards, maybe because the magnetic module was not level.
    topOffset = -5 # I use this to make sure the tip stays inside the well, to avoid it spilling out while dispensing
    tipVolume = 200 # ul
        #Transference volumes - ul
    originalVol = 140
    proteinaseVol= 112
    beadsVol= 144
    initialSupernatant = originalVol + proteinaseVol + beadsVol
    washVol= 280
    dilutionVol= 80
        #Mixing volumes - In ul
    washMixing=100
    beadsMixing=200
    beadsHeight=30
    mixRepeats=5
        #Incubation times - Minutes
    incubationProteinase = 10
    incubationBeadsNoMagnet = 5
    incubationBeadsMagnet = 5
    incubationWash = 3
    incubationWater = 1

    # izda= True # Deprecated. I used this to code the pipette offset when removing supernatant to move away of pellet. Unnecesary now, cause whe dont use whole plate.

    #Functions
    def remove_tip(tip):
        """Deprecated, but makes it easy to force the robot to not drop tips, so I still use it."""
        p300.drop_tip()

    def retrieve_tip(tip):
        """Originally, the robot took a tip, went to the top of the well it was going to work with, and aspired 20 ul there, but now we are making it aspire 20 ul after taking the tip"""
        p300.pick_up_tip(tip)
        p300.aspirate(20)

    def well_mix(loc, vol, reps, height=5.5):
        """Aspirates <vol> from bottom of well and dispenses it from 5.5 mm of height <reps> times"""
        loc1 = loc.bottom().move(types.Point(x=0, y=0, z=0.6))
        loc2 = loc.bottom().move(types.Point(x=0, y=0, z=height))
        for _ in range(reps-1):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc2)
        p300.dispense(20, loc.top(topOffset))

    def remove_supernatant(src, vol, dump, izda=True):
        """While <vol> is bigger than 180ul, it divides it in 180ul trips.
        Flow rate is in ul/second
        Positive X means to move to the right. With the wells we use (Column 1,3,5,7,9 and 11) pellet is placed to the right, so we use a small offset to the left"""
        p300.flow_rate.aspirate = 20
        tvol = vol
        while tvol > tipVolume:
            p300.dispense(20, src.top(topOffset) )
            p300.transfer(tipVolume, src.bottom().move(types.Point(x=-1, y=0, z=0.5)), dump.top(topOffset), new_tip="never") #Slightly to the left
            protocol.delay(seconds=2) #In case something is TheOppositeOfDense and just drips down
            p300.blow_out() #Make sure we expel everything that must be expelled. We dont want to move droplets around.
            tvol -= tipVolume
        p300.dispense(20, src.top(topOffset) )
        p300.transfer(tvol, src.bottom().move(types.Point(x=-1, y=0, z=0.5)), dump.top(topOffset), new_tip="never")
        protocol.delay(seconds=2)
        p300.flow_rate.aspirate = 50

    def slow_transfer(vol, src, to):
        """Similar to remove_supernatant, but the other way around. It transfers from point A to point B in 200ul trips and pours liquid
        from the top, to avoid contaminating the tip while transfering all the necessary volume"""
        tvol = vol
        while tvol > tipVolume:
            p300.dispense(20, src.top() )
            p300.transfer(tipVolume, src.bottom().move(types.Point(x=0, y=0, z=0.5)), to.top(topOffset), new_tip="never")
            protocol.delay(seconds=2)
            p300.blow_out()
            tvol -= tipVolume
        p300.dispense(20, src.top() )
        p300.transfer(tvol,src.bottom().move(types.Point(x=0, y=0, z=0.5)), to.top(topOffset), new_tip="never")
        protocol.delay(seconds=2)
        p300.dispense(20)

    #These next functions are more specific.

    def removing_step(vol, wasteID, columnID, reagentName="Something"):
        """There are 4 steps of supernatant removal which are pretty much similar"""
        protocol.comment("\n\nREMOVING STEP: Removing %s ul of supernatant (%s) while magnet is still engaged" % (vol, reagentName) )
        for index, ID in enumerate(columnID):
            currentip = availableTips.pop()
            retrieve_tip(currentip)
            remove_supernatant(src=deepPlate[ID], vol=vol, dump=waste[wasteID])
            remove_tip(currentip)

    def adding_step(vol, reagent, reagentName, incubationTime, columnID, mixVol=washMixing, repeats=mixRepeats, mixReagent=False, magnetTime=True):
        """Same as before, but adding"""
        protocol.comment("\n\nADDING STEP: Transfering %s ul of %s to samples" % (vol, reagentName))
        for index, ID in enumerate(columnID):
            currentip = availableTips.pop()
            retrieve_tip(currentip)
            if (mixReagent==True):
                protocol.comment("Mixing magnetic beads")
                well_mix(loc=beads, vol=beadsMixing, reps=mixRepeats, height=beadsHeight)
                p300.blow_out(beads.top())
                mixReagent=False
            slow_transfer(vol=vol, src=reagent, to=deepPlate[ID])
            well_mix(loc=deepPlate[ID], vol=mixVol, reps=repeats)
            remove_tip(currentip)
        #Incubation
        if magnetTime==True:
            protocol.comment("Engaging magnet")
            magneto.engage(height=magnetHeight)
        protocol.comment("Incubating for %s minutes" % incubationTime)
        protocol.delay(minutes=incubationTime)

    ##############################################################################################
    # C O M M A N D S || Hello, actual protocol!

        #STEP 1: Add Proteinase K/LBF. I don't use the adding_step function here because there are slight variations which I don't want to add to the function

    protocol.comment("We are working with column IDs: %s" % columnID)
    protocol.comment("\n\nSamples should have an initual volume of 140ul")
    adding_step(vol= proteinaseVol, reagent=proteinase, reagentName="Proteinase K/LBF", incubationTime=incubationProteinase,
    columnID=columnID, magnetTime=False)
    #INCUBATION 1: 10 min [Total: 10 min]


        #STEP 2: mix magnetic beads, add them to samples and mix sample well. No adding_step function for the same reasons as before.
    protocol.comment("\n\nEnough incubation, time to do s t u f f")
    iteration = 0
    adding_step(vol=beadsVol, reagent=beads, reagentName="Magnetic beads", incubationTime=incubationBeadsNoMagnet,
    columnID=columnID, mixReagent=True, magnetTime=False)
    #INCUBATION 2: 5 min without magnet [Total: 15 min]
    protocol.comment("Engaging magnet and keeping this incubation going for other %s minutes" % incubationBeadsMagnet)
    magneto.engage(height=magnetHeight)
    protocol.delay(minutes=5)
    #INCUBATION 3: 5 min incubation with magnet [Total: 20 min]


        #STEP 3: Remove magnetic beads supernatant
    removing_step(vol= initialSupernatant, wasteID="A1", reagentName="beads and proteinase",
    columnID=columnID)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 4: Add 280 ul of Wash WBE
    adding_step(vol= washVol, reagent=WBE, reagentName="WBE", incubationTime=incubationWash,
    columnID=columnID)
        #INCUBATION 4: 3 min incubaton with magnet [Total: 23 min]


        #STEP 5: Removing WBE Supernatant
    removing_step(vol= washVol, wasteID="A2", reagentName="WBE",
    columnID=columnID)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 6: First wash with Eth, tips_transfer)anol
    adding_step(vol= washVol, reagent=ethanol, reagentName="Ethanol 70% (First time)", incubationTime=incubationWash,
    columnID=columnID)
        #INCUBATION 5: 3 min incubaton with magnet [Total: 26 min]


        #STEP 7: Removing the supernatant of first wash with Ethanol
    removing_step(vol= washVol, wasteID="A3", reagentName="Ethanol 70% (First time)",
    columnID=columnID)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 8: Second wash with Ethanol
    adding_step(vol= washVol, reagent=ethanol, reagentName="Ethanol 70% (Second time)", incubationTime=incubationWash,
    columnID=columnID)
        #INCUBATION 6: 3 min incubaton with magnet [Total: 26 min]


        #STEP 9: Removing the supernatant of second wash with Ethanol
    removing_step(vol=washVol, wasteID="A4", reagentName="Ethanol 70% (Second time)",
    columnID=columnID)

        #INCUBATION 7: 5 min incubaton with magnet [Total: 31 min]
    protocol.comment("This time, I do not disengage the magnet and let the beads dry for 5 min")
    protocol.delay(minutes=5)

        #STEP 10: Diluting samples in 80 ul of RNAse free water
    protocol.comment("Disengaging magnet")
    magneto.disengage()
    protocol.comment("Diluting samples in %s ul of RNAse free water" % dilutionVol)
    adding_step(vol= dilutionVol, reagent=water, reagentName="RNAse-free water",incubationTime=incubationWater,
    columnID=columnID, mixVol=30)
        #INCUBATION 7: 1 min incubaton with magnet [Total: 32 min]

        #STEP 11: Transfering samples to output eppendorf 96 well plate
    protocol.comment("Transfering DNA to output plate")
    magneto.disengage()
    for index, ID in enumerate(columnID):
        currentip = availableTips.pop()
        retrieve_tip(currentip)
        slow_transfer(dilutionVol, deepPlate[ID], outplate[ID])
        remove_tip(currentip)

    protocol.comment("\n\nFecho!")
