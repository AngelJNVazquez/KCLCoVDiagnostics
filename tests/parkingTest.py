from opentrons import protocol_api, types
import json

metadata =  {
    "protocolName": "Beckman RNA extraction protocol",
    "author": "Angel Menendez Vazquez <angel.menendez_vazquez@kcl.ac.uk>",
    "description": "As RNA template 25/06/20 but with faster speed and higher mixing",
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
    magnetHeight= 6.7
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
    outplate = protocol.load_labware("eppendorf96_skirted_150ul", 1, label = "Output plate")
        #Tips - Ordered in the way they are used
    parkingRack = protocol.load_labware("opentrons_96_filtertiprack_200ul", 3)
    tiprack1 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 2)
    tiprack4 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    tiprack7 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 7)
    tiprack8 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 8)
    tiprack10 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 10)

    tipracks = [tiprack10, tiprack8, tiprack7, tiprack4, tiprack1]
    availableTips = []
    for rack in tipracks:
        for i in range(1,13):
            availableTips.append(rack["A"+str(i)])
    #To take a tip, just use availableTips.pop() and voila!
    #There are enough tips for 6 samples, and a tiprack will end up half-full
    #Tips are taken from right to left instead of the normal way
    #I am using this dictionary method because it makes it easier to modify later the script for 96 samples/

        #Pipettes
    p300 = protocol.load_instrument( "p300_multi_gen2", "left")

    ################### SETTING UP ###################
    ##                                              ##
    ## ヽ༼ຈل͜ຈ༽ﾉ BASIC VARIABLES ヽ༼ຈل͜ຈ༽ﾉ           ##
    ##                                              ##
    ##################################################

        #RUN SETTINGS
    runColumns = 2 # Range 1-6. Samples should be a multiple of 8, or you will waste reagents.
    mixRepeats = 15 # Used everytime there is mixing, except when mixing beads.
    beadsMixRepeats = 10 # Used when mixing beads in reservoir. This happens when pipetting column 1, 3 and 6.
    waterMixRepeats = 20 # Used when mixing elute.

        #Mixing settings
    washMixing = 100 # volume (ul)
    waterMixing = 25 # volume (ul)
    bottomHeight = 0.5 # Distance relative to real labware's bottom. Used when removing supernatant and moving elution.
    bottomMixHeight = 0.8 # Distance relative to real labware's bottom. Used when mixing
    SamplePlusProteinaseHeight = 3 # For a volume of 260..
    SamplePlusProteinasePlusBeadsHeight = 5.75 # For a volume of 465...
    generalHeight = 4 # Used always except when mixing beads in reservoir - Units relative to well bottom (mm). For a vol of 280...
    beadsHeight = 10 # Used when mixing beads in reservoir - Units relative to well bottom (mm). When mixing beads in the reagent well - Maybe I should modify this and make it depend on runColumns

        #Incubation times - Minutes
    incubationProteinase = 10
    incubationBeadsNoMagnet = 5 # After adding the beads, we incubate them for 5 min without magnet.
    incubationBeadsMagnet = 5
    incubationWash = 3
    incubationDry = 10 # After removing final wash, the beads are left to dry for a while.
    incubationWater = 5 # After mixing. No magnet.
    incubationWaterMagnet = 1 # After incubationWater.

        #Transference volumes - ul
    originalVol = 140 #This is not used for transfers, it is here mostly to make volumes clearer to understand
    proteinaseVol = 112
    beadsVol = 143.5
    washVol = 280 #Used for WBE and Ethanol1 and Ethanol2
    dilutionVol = 50
    initialSupernatant = originalVol + proteinaseVol + beadsVol

        #Reagent position in reservoir - Positions go from A1 to A12 (Left to right)
    proteinase = reagents["A1"]
    beads = reagents["A2"]
    WBE = reagents["A3"]
    ethanol1 = reagents["A4"]
    ethanol2 = reagents["A5"]
    water = reagents["A12"]
    #########################################################################################################
    ##           Use these formulae to identify how much volume you need based on number of columns        ##
    ##           Each reservoir well has dimensions W=8.20, L=127.76, H=31.40. To make sure there is       ##
    ##           a pool of extra content with 0.5mm of height, add 292ul (300) extra (8.20*127.76*0.05)    ##
    ##                                                                                                     ##
    ##  Proteinase = (896 * runColumns) + 292 ul                                                           ##
    ##  Beads = (1152 * Columns) + 292 ul                                                                  ##
    ##  WBE = (2240 * Columns) + 292 ul                                                                    ##
    ##  Ethanol1 = (2240 * Columns) + 292 ul                                                               ##
    ##  Ethanol2 = (2240 * Columns) + 292 ul                                                               ##
    ##  Water = (640 * Columns) + 292 ul                                                                   ##
    #########################################################################################################

    ################### SETTING UP ###################
    ##                                              ##
    ## ヽ༼ຈل͜ຈ༽ﾉ ADVANCED VARIABLES ヽ༼ຈل͜ຈ༽ﾉ          ##
    ##                                              ##
    ##################################################

        #Column accesion list - As we wont work in all physically available columns, this list makes it easier to manage
    columnID = ["A1", "A3", "A5", "A7", "A9", "A11"] # These are the columns that can be used
    columnID = columnID[:runColumns] # Here we trim the list, to get only the number of columns chosen in runColumns

        #Pipette settings
    tipVolume = 180 # max volume to be transported in a single trip. These tips are 200ul, but if we use the entire volumen, it might touch the filter
    topOffset = -5 # I use this to make sure the tip stays inside the well, to avoid it spilling out while dispensing
    p300.flow_rate.aspirate = 50 # Flow rate in ul / second
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 200
    #Flows are reduced compared to default values to avoid the production of air or foam during handling.

        #Volume used when mixing beads (ul)
    if runColumns==1:
        beadsMixing=140
    else:
        beadsMixing=tipVolume




    ################### SETTING UP ###################
    ##                                              ##
    ##(づ｡◕‿‿◕｡)づ    FUNCTIONS    (づ｡◕‿‿◕｡)づ ##
    ##                                              ##
    ##################################################
    def clock(time):
        """
        The uncertainty of not knowing how much time is left in an incubation is horrible. This makes it more bearable.
        This function takes the duration of the incubation and outputs a message every minute to keep track of the time more easily
        """
        while time > 0:
            time -= 1
            protocol.delay(seconds=1)
            protocol.comment("Only %s minutes more! Hold in there!" % time)

    def meneillo(pipette, pos, reps=20, distance=0.25):
        pipette.move_to(pos)
        for _ in range(20):
            p300.move_to(pos.move(types.Point(x=0.25,y=0,z=0)))
            p300.move_to(pos.move(types.Point(x=-0.25,y=0,z=0)))

    def remove_tip(pipette, tip):
        """
        Originally, I had a special behaviour to drop the tips, but I stopped using it.
        I keep this function because it makes it easy to change drop_tip() to return_tip() for test runs
        """
        pipette.return_tip()

    def retrieve_tip(pipette, tip):
        """
        Originally, the robot took a tip, went to the top of the well it was going to work with, and aspired 20 ul there, but now we are making it aspire 20 ul after taking the tip
        """
        pipette.pick_up_tip(tip)

    def well_mix(vol, loc, reps, height=generalHeight, moveSide=0, bottomHeight = bottomMixHeight):
        """
        Aspirates <vol> from bottom of well and dispenses it from <height> <reps> times
        loc1 is a position at 0.3mm over the bottom of the well
        loc2 is a position in the same x and y posiiton than loc1, but at <height>mm over the bottom of the well
        The idea here is to take liquid to the very bottom and pour it from a higher point, to mix things
        """
        p300.flow_rate.aspirate = 1000
        p300.flow_rate.dispense = 1000
        loc1 = loc.bottom().move(types.Point(x=0+moveSide, y=0, z=bottomHeight))
        loc2 = loc.bottom().move(types.Point(x=0+moveSide, y=0, z=height))
        for _ in range(reps):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc2)
        p300.dispense(20, loc.top(topOffset))
        p300.flow_rate.aspirate = 50
        p300.flow_rate.dispense = 150

    def remove_supernatant(vol, columnID, wasteID, reagentName="Something", pipette=p300):
        """
        While <vol> is bigger than <tipVolume>, it divides it in ceilling(<vol>/<tipVolume>) trips. (So, if it is 396ul, we have 2 180ul trips and a 36ul trip)
        Flow rate is in ul/second
        In the move() function, positive X means 'move to the right'. With the wells we use (Column 1,3,5,7,9 and 11) pellet is placed to the right, so we use a small offset to the left
        """
        p300.flow_rate.aspirate = 20 # In this case we reduce the flow even more to make sure the precipitate is okay. We don't wanna bother the lad
        protocol.comment("\n\nREMOVING STEP: Removing %s ul of supernatant (%s) while magnet is still engaged" % (vol, reagentName) )
        dump=waste[wasteID]
        for index, ID in enumerate(columnID):
            currentip = parkingRack[ID]
            dump = waste[ID]
            src = deepPlate[ID]
            retrieve_tip(pipette, currentip)
            tvol = vol
            while tvol > tipVolume:
                p300.dispense(20, src.top(topOffset) )
                p300.transfer(tipVolume, src.bottom().move(types.Point(x=-1, y=0, z=bottomHeight)), dump.top(topOffset), new_tip="never") #Slightly to the left
                protocol.delay(seconds=2) #In case something is TheOppositeOfDense and just drips down
                p300.dispense(20) #Make sure we expel everything that must be expelled. We dont want to move droplets around.
                tvol -= tipVolume
            p300.dispense(20, src.top(topOffset) )
            p300.transfer(tvol, src.bottom().move(types.Point(x=-1, y=0, z=bottomHeight)), dump.top(topOffset), new_tip="never")
            meneillo(p300, dump.top(topOffset))
            remove_tip(pipette, currentip)
        p300.flow_rate.aspirate = 50


    def slow_transfer(vol, reagent, columnID, reagentName,
    mixVol=washMixing, repeats=mixRepeats,
    mixReagent=False, altura=generalHeight,
    magnetTime=True, incubationTime = incubationWash,
    moveSide=0, extraVol=0, pipette=p300, removalStepAfter = True):
        """
        Similar to remove_supernatant, but the other way around. It transfers from point A to point B in <tipVol> ul trips and pours liquid
        from the top, to avoid contaminating the tip while transfering all the necessary volume.
        It also includes incubation and magnet
        """
        protocol.comment("\n\nADDING STEP: Transfering %s ul of %s to samples" % (vol, reagentName))
        for index, ID in enumerate(columnID):
            src=reagent
            to=deepPlate[ID]
            currentip = availableTips.pop()
            retrieve_tip(p300, currentip)
            if (mixReagent==True) and (index==0 or index==2 or index==5): #If the reagent is to be mixed, and we are in column 1, 3 or 6, mix it. We mix three times to make sure we dont have differences
                protocol.comment("Mixing %s" % reagentName)
                well_mix(vol=beadsMixing, loc=beads, reps=beadsMixRepeats, height=beadsHeight, moveSide=0) #We only do this with magnetic beads, that's why we use those variable names
                p300.blow_out(beads.top())
            tvol = vol
            while tvol > tipVolume:
                p300.dispense(20, src.top() )
                p300.transfer(tipVolume, src.bottom().move(types.Point(x=0, y=0, z=bottomHeight)),
                to.top(topOffset), new_tip="never", air_gap=extraVol)
                protocol.delay(seconds=2)
                p300.blow_out()
                tvol -= tipVolume
            p300.dispense(20, src.top() )
            p300.transfer(tvol,src.bottom().move(types.Point(x=0, y=0, z=bottomHeight)),
            to.center(), new_tip="never", air_gap=extraVol)
            protocol.delay(seconds=2)
            well_mix(vol=mixVol, loc=to, reps=repeats, moveSide=moveSide, height=altura)
            if removalStepAfter == True:
                pipette.drop_tip(parkingRack[ID])
            else:
                remove_tip(pipette, currentip)

        #Incubation
        if magnetTime==True:
            protocol.comment("Engaging magnet")
            magneto.engage(height=magnetHeight)
        protocol.comment("Incubating for %s minutes" % incubationTime)
        clock(time=incubationTime)

    ################# GO, VASILY, GO #################
    ##                                              ##
    ##      ୧༼ಠ益ಠ༽୨    PROTOCOL    ୧༼ಠ益ಠ༽୨        ##
    ##                                              ##
    ##################################################

    magneto.disengage() #In case it is engaged from previous protocols.
    protocol.comment("We are working with column IDs: %s" % columnID)
    protocol.comment("\n\nSamples should have an initial volume of %s ul" % originalVol)

        #STEP 1: Add Proteinase K/LBF.
    slow_transfer(vol= proteinaseVol, reagent=proteinase, reagentName="Proteinase K/LBF", incubationTime=incubationProteinase,
    columnID=columnID, magnetTime=False, altura=SamplePlusProteinaseHeight, removalStepAfter = False)
    #INCUBATION 1: 10 min [Total: 10 min]

        #STEP 2: mix magnetic beads, add them to samples and mix sample well. No slow_transfer function for the same reasons as before.
    protocol.comment("\n\nEnough incubation, time to do s t u f f")
    slow_transfer(vol=beadsVol, reagent=beads, reagentName="Magnetic beads", incubationTime=incubationBeadsNoMagnet,
    columnID=columnID, mixReagent=True, magnetTime=False, extraVol=10, altura=SamplePlusProteinasePlusBeadsHeight)
    #INCUBATION 2: 5 min without magnet [Total: 15 min]
    protocol.comment("Engaging magnet and keeping this incubation going for other %s minutes" % incubationBeadsMagnet)
    magneto.engage(height=magnetHeight)
    clock(time=incubationBeadsMagnet)
    #INCUBATION 3: 5 min incubation with magnet [Total: 20 min]

        #STEP 3: Remove magnetic beads supernatant
    remove_supernatant(vol= initialSupernatant, wasteID="A1", reagentName="beads and proteinase",
    columnID=columnID)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 4: Add 280 ul of Wash WBE
    slow_transfer(vol= washVol, reagent=WBE, reagentName="WBE", incubationTime=incubationWash,
    columnID=columnID)
        #INCUBATION 4: 3 min incubaton with magnet [Total: 23 min]

        #STEP 5: Removing WBE Supernatant
    remove_supernatant(vol= washVol, wasteID="A2", reagentName="WBE",
    columnID=columnID)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 6: First wash with Eth, tips_transfer)anol
    slow_transfer(vol= washVol, reagent=ethanol1, reagentName="Ethanol 70% (First time)", incubationTime=incubationWash,
    columnID=columnID)
        #INCUBATION 5: 3 min incubaton with magnet [Total: 26 min]

        #STEP 7: Removing the supernatant of first wash with Ethanol
    remove_supernatant(vol= washVol, wasteID="A3", reagentName="Ethanol 70% (First time)",
    columnID=columnID)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 8: Second wash with Ethanol
    slow_transfer(vol= washVol, reagent=ethanol2, reagentName="Ethanol 70% (Second time)", incubationTime=incubationWash,
    columnID=columnID)
        #INCUBATION 6: 3 min incubaton with magnet [Total: 26 min]

        #STEP 9: Removing the supernatant of second wash with Ethanol
    remove_supernatant(vol=washVol, wasteID="A4", reagentName="Ethanol 70% (Second time)",
    columnID=columnID)
        #INCUBATION 7: 5 min incubaton with magnet [Total: 31 min]
    protocol.comment("This time, I do not disengage the magnet and let the beads dry for %s min" % incubationDry)
    clock(time=incubationDry)

        #STEP 10: Diluting samples in 80 ul of RNAse free water
    protocol.comment("Disengaging magnet")
    magneto.disengage()
    protocol.comment("Diluting samples in %s ul of RNAse free water" % dilutionVol)
    slow_transfer(vol= dilutionVol, reagent=water, reagentName="RNAse-free water",
    incubationTime=incubationWater, columnID=columnID, mixVol=waterMixing,
    magnetTime=False, repeats=waterMixRepeats) #Moving tip on top of pellet
        #INCUBATION 8: 5 min incubaton WITHOUT magnet [Total: 36 min]
    protocol.comment("Engaging magnet now!")
    magneto.engage(height=magnetHeight)
    clock(time=incubationWaterMagnet)
        #INCUBATION 9: 3 min incubaton WITH magnet [Total: 39 min]

        #STEP 11: Transfering samples to output plate
    protocol.comment("Transfering DNA to output plate while magnet is still engaged")
    p300.flow_rate.aspirate = 20
    for index, ID in enumerate(columnID):
        currentip = parkingRack[ID]
        retrieve_tip(p300, currentip)
        src = deepPlate[ID]
        to = outplate[ID]

        p300.dispense(20, src.top() )
        p300.transfer(dilutionVol, src.bottom().move(types.Point(x=-1, y=0, z=bottomHeight)),
        to.bottom(5), new_tip="never")
        protocol.delay(seconds=2)
        p300.dispense(20)
        remove_tip(p300, currentip)

    magneto.disengage()
    protocol.comment("\n\nFecho!")
