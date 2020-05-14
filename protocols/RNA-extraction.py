from opentrons import protocol_api, types
import json

metadata =  {
    "protocolName": "Beckman RNA extraction protocol",
    "author": "Angel Menendez Vazquez <angel.menendez_vazquez@kcl.ac.uk>",
    "description": "Protocol for RNA extraction on 48 samples based on a SOP for 'Viral RNA Extraction with Beckman RNAdvance' and this script https://github.com/Opentrons/covid19/blob/master/protocols/OMI_Clinical/StationB_Zymo_20200407/StationB-48samples-Zymo-20200407.py",
    "apiLevel": "2.3"
}

def run(protocol: protocol_api.ProtocolContext):

    ################### SETTING UP ###################
    ##                                    ##
    ##     ヽ༼ຈل͜ຈ༽ﾉ LABWARE ヽ༼ຈل͜ຈ༽ﾉ     ##
    ##                                    ##
    ##################################################

                # Positions are:
                # 10    11      TRASH
                # 7     8       9
                # 4     5       6
                # 1     2       3

        #Modules, plate and MAGNET HEIGHT
    magneto = protocol.load_module("magdeck", 6)
    deepPlate = magneto.load_labware("eppendorf_96_deepwell_2ml", label = "Deep well")
    magnetHeight= 11.8
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
    tiprack2 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 2)
    tiprack1 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 1)
    tiprack4 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    tiprack7 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 7)
    tiprack8 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 8)
    tiprack10 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 10)

    tipracks = [tiprack10, tiprack8, tiprack7, tiprack4, tiprack1, tiprack2]
    availableTips = []
    for rack in tipracks:
        for i in range(1,13):
            availableTips.append(rack["A"+str(i)])
    #To take a tip, just use availableTips.pop() and voila!
    #There are enough tips for 6 samples, and a tiprack will end up half-full
    #Tips are taken from right to left instead of the normal way
    #I am using this dictionary method because it makes it easier to modify later the script for 96 samples/

        #Pipettes
    p300 = protocol.load_instrument( "p300_multi", "left")

    ################### SETTING UP ###################
    ##                                    ##
    ## ヽ༼ຈل͜ຈ༽ﾉ BASIC VARIABLES ヽ༼ຈل͜ຈ༽ﾉ ##
    ##                                    ##
    ##################################################

        #RUN SETTINGS
    runColumns=1 # Range 1-6. Samples should be a multiple of 8, or you will waste reagents.
    mixRepeats=7 # Used everytime there is mixing, except when mixing beads.
    beadsMixRepeats=10

        #Mixing settings
    washMixing=100 # volume (ul)
    waterMixing=25 # volume (ul)
    generalHeight=5 # Used always except when mixing beads in reservoir - Beads are extracted from From well bottom (mm)
    beadsHeight=10 # Used when mixing beads in reservoir - From well bottom (mm). When mixing beads in the reagent well - Maybe I should modify this and make it depend on runColumns

        #Incubation times - Minutes
    incubationProteinase = 10
    incubationBeadsNoMagnet = 5 # After adding the beads, we incubate them for 5 min without magnet.
    incubationBeadsMagnet = 5
    incubationWash = 3
    incubationDry = 5 # After removing final wash, the beads are left to dry for a while.
    incubationWater = 1

        #Transference volumes - ul
    originalVol = 140 #This is not used for transfers, it is here mostly to make volumes clearer to understand
    proteinaseVol= 112
    beadsVol= 144
    washVol= 280 #Used for WBE and Ethanol1 and Ethanol2
    dilutionVol= 50
    initialSupernatant = originalVol + proteinaseVol + beadsVol

        #Reagent position in reservoir - Positions go from A1 to A12 (Left to right)
    proteinase = reagents["A1"] # (896 * Columns) + 292 ul
    beads = reagents["A2"] # (1152 * Columns) + 292 ul
    WBE = reagents["A3"] # (2240 * Columns) + 292 ul
    ethanol1 = reagents["A4"] # (2240 * Columns) + 292 ul
    ethanol2 = reagents["A5"] # (2240 * Columns) + 292 ul
    water = reagents["A6"] # (640 * Columns) + 292 ul
    #########################################################################################################
    ##           Use these formulae to identify how much volume you need based on number of columns        ##
    ##           Each reservoir well has dimensions W=8.20, L=127.76, H=31.40. To make sure there is       ##
    ##           a pool of extra content with 0.5mm of height, add 292ul (300) extra (8.20*127.76*0.05)    ##
    ##                                                                                                     ##
    ##  Proteinase = (896 * runColumns) + 292                                                              ##
    ##  Beads = (1152 * Columns) + 292 ul                                                                  ##
    ##  WBE = (2240 * Columns) + 292 ul                                                                    ##
    ##  Ethanol1 = (2240 * Columns) + 292 ul                                                               ##
    ##  Ethanol2 = (2240 * Columns) + 292 ul                                                               ##
    ##  Water = (640 * Columns) + 292 ul                                                                   ##
    #########################################################################################################

    ################### SETTING UP ###################
    ##                                    ##
    ## ヽ༼ຈل͜ຈ༽ﾉ ADVANCED VARIABLES ヽ༼ຈل͜ຈ༽ﾉ ##
    ##                                    ##
    ##################################################

        #Column accesion list - As we wont work in all physically available columns, this list makes it easier to manage
    columnID = ["A"+str(i) for i in range(1,12,2)]
    columnID = columnID[:runColumns]

        #Pipette settings
    tipVolume = 180 # max volume to be transported in a single trip
    topOffset = -5 # I use this to make sure the tip stays inside the well, to avoid it spilling out while dispensing
    p300.flow_rate.aspirate = 50 # Flow rate in ul / second
    p300.flow_rate.dispense = 150
    p300.flow_rate.blow_out = 300

        #Volume used when mixing beads (ul)
    if runColumns==1:
        beadsMixing=140
    else:
        beadsMixing=tipVolume




    ################### SETTING UP ###################
    ##                                              ##
    ##   (づ｡◕‿‿◕｡)づ    FUNCTIONS    (づ｡◕‿‿◕｡)づ    ##
    ##                                              ##
    ##################################################
    def clock(time):
        """The uncertainty of not knowing how much time is left in an incubation is horrible. This makes it more bearable"""
        while time > 0:
            protocol.comment("Only %s minutes more!" % time)
            protocol.delay(minutes=1)
            time -= 1

    def remove_tip(tip):
        """Originally, I had a special behaviour to drop the tips, but I stopped using it. I keep this function because it makes it easy to change drop_tip() to return_tip() for test runs"""
        p300.drop_tip()

    def retrieve_tip(tip):
        """Originally, the robot took a tip, went to the top of the well it was going to work with, and aspired 20 ul there, but now we are making it aspire 20 ul after taking the tip"""
        p300.pick_up_tip(tip)
        p300.aspirate(20)

    def well_mix(loc, vol, reps, height=generalHeight):
        """Aspirates <vol> from bottom of well and dispenses it from <height> <reps> times"""
        loc1 = loc.bottom().move(types.Point(x=0, y=0, z=0.6))
        loc2 = loc.bottom().move(types.Point(x=0, y=0, z=height))
        for _ in range(reps-1):
            p300.aspirate(vol, loc1)
            p300.dispense(vol, loc2)
        p300.dispense(20, loc.top(topOffset))

    def remove_supernatant(src, vol, dump, izda=True):
        """While <vol> is bigger than <tipVolume>, it divides it in ceilling(<tipVolume>//<vol>) trips.
        Flow rate is in ul/second
        Positive X means 'move to the right'. With the wells we use (Column 1,3,5,7,9 and 11) pellet is placed to the right, so we use a small offset to the left"""
        p300.flow_rate.aspirate = 20 # Do not wanna bother the precipitate.
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
        """Similar to remove_supernatant, but the other way around. It transfers from point A to point B in tipVol ul trips and pours liquid
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

    ############################################################################
    #These next functions are more specific. Combinations of the previous ones.#
    ############################################################################

    def removing_step(vol, wasteID, columnID, reagentName="Something"):
        """There are 4 steps of supernatant removal which are pretty much similar. This function iterates over each column"""
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
                well_mix(loc=beads, vol=beadsMixing, reps=beadsMixRepeats, height=beadsHeight)
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
        clock(time=incubationTime)

    ################# GO, VASILY, GO #################
    ##                                              ##
    ##      ୧༼ಠ益ಠ༽୨    PROTOCOL    ୧༼ಠ益ಠ༽୨        ##
    ##                                              ##
    ##################################################

    magneto.disengage() #In case it is engaged from previous protocols.
    protocol.comment("We are working with column IDs: %s" % columnID)
    protocol.comment("\n\nSamples should have an initial volume of 140ul")

        #STEP 1: Add Proteinase K/LBF.
    adding_step(vol= proteinaseVol, reagent=proteinase, reagentName="Proteinase K/LBF", incubationTime=incubationProteinase,
    columnID=columnID, magnetTime=False)
    #INCUBATION 1: 10 min [Total: 10 min]

        #STEP 2: mix magnetic beads, add them to samples and mix sample well. No adding_step function for the same reasons as before.
    protocol.comment("\n\nEnough incubation, time to do s t u f f")
    adding_step(vol=beadsVol, reagent=beads, reagentName="Magnetic beads", incubationTime=incubationBeadsNoMagnet,
    columnID=columnID, mixReagent=True, magnetTime=False)
    #INCUBATION 2: 5 min without magnet [Total: 15 min]
    protocol.comment("Engaging magnet and keeping this incubation going for other %s minutes" % incubationBeadsMagnet)
    magneto.engage(height=magnetHeight)
    clock(time=incubationBeadsMagnet)
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
    adding_step(vol= washVol, reagent=ethanol1, reagentName="Ethanol 70% (First time)", incubationTime=incubationWash,
    columnID=columnID)
        #INCUBATION 5: 3 min incubaton with magnet [Total: 26 min]

        #STEP 7: Removing the supernatant of first wash with Ethanol
    removing_step(vol= washVol, wasteID="A3", reagentName="Ethanol 70% (First time)",
    columnID=columnID)
    protocol.comment("Disengaging magnet")
    magneto.disengage()

        #STEP 8: Second wash with Ethanol
    adding_step(vol= washVol, reagent=ethanol2, reagentName="Ethanol 70% (Second time)", incubationTime=incubationWash,
    columnID=columnID)
        #INCUBATION 6: 3 min incubaton with magnet [Total: 26 min]

        #STEP 9: Removing the supernatant of second wash with Ethanol
    removing_step(vol=washVol, wasteID="A4", reagentName="Ethanol 70% (Second time)",
    columnID=columnID)
        #INCUBATION 7: 5 min incubaton with magnet [Total: 31 min]
    protocol.comment("This time, I do not disengage the magnet and let the beads dry for 5 min")
    clock(time=incubationDry)

        #STEP 10: Diluting samples in 80 ul of RNAse free water
    protocol.comment("Disengaging magnet")
    magneto.disengage()
    protocol.comment("Diluting samples in %s ul of RNAse free water" % dilutionVol)
    adding_step(vol= dilutionVol, reagent=water, reagentName="RNAse-free water",incubationTime=incubationWater,
    columnID=columnID, mixVol=waterMixing)
        #INCUBATION 7: 1 min incubaton with magnet [Total: 32 min]

        #STEP 11: Transfering samples to output plate
    protocol.comment("Transfering DNA to output plate while magnet is still engaged")
    for index, ID in enumerate(columnID):
        currentip = availableTips.pop()
        retrieve_tip(currentip)
        slow_transfer(dilutionVol, deepPlate[ID], outplate[ID])
        remove_tip(currentip)

    magneto.disengage()
    protocol.comment("\n\nFecho!")
