'''###############################################################################################################################
Author: Felipe Sanges - 2013

Nurbs ribbon tool with a variable layer count and weighted influences. The ribbon has a variable numbers of skinClusters 
layered with a variable number of joints evenly spaced in U and/or V directions. Weights are automatically calculated 
according to the number of joints in it's skinCluster.

This script is a work in progress. There's a lot of improvements to be made and I apologize for the dirty code :/
ToDo:
        -Recreate UI with QT
        -Fix locked attrs
        -Define return values
        -Adjust prefix - (Done)
        -A hole bunch of stuff
DEPENDENCIES:
        -controlCurveShapes.py
'''

import maya.cmds as mc
import maya.mel as mel
import string
import maya.OpenMaya as om

# Import shape module
import controlCurveShapes as ccs
reload(ccs)


def createRibbon(
    scale=0.10,
    edgeAtOrigin=True,
    drivenSurface=True,
    bends=0,
    selected=False,
    width=1.0,
    height=1.0,
    name='fsRibbon',
    oneDimension=True,
    numLayers=4,
    lyrDensityU=(1, 1, 2, 5),
    lyrDensityV=(1, 1, 1, 1, 1),
    autoCtrlCurves=True,
    rotationOn = True,
    direction = 'u',
    createOutMesh = True
    ):

    '''-
    Description:
        Creates a layered controlled ribbon.
        Dependencies:
        Usage Example:
            test = createRibbon()[4]
            createRibbon(autoCtrlCurves=False, drivenSurface=False, name='ohYeah')
            createRibbon
                (
                scale=0.10,                 # = Controls scale
                edgeAtOrigin=True,          # = The base of the ribbon will start at the origin of the world.
                drivenSurface=True,         # = Creates a deformer surface that driver the ribbon setup. Ex. "spine_lyr_D_surfDeformer"
                bends=0,                    # = Made for paper rig only
                selected=False,             # = Use selected surface. BROKEN
                width=1.0,
                name='fsRibbon1',           # = Prefix for the entire rig
                oneDimension=True,          # = One dimension line of controls or 2d plane with collumns and rows of cotrols - BROKEN
                numLayers=4,                # = Number of control layers
                lyrDensityU=[1, 1, 2, 5],   # = Number of control per layer in U
                lyrDensityV=[1, 1, 1, 1, 1] # = Number of control per layer in V
                )
    '''


    surfLyr = ['A', 'B', 'C', 'D', 'E', 'F']

    LETTERS = string.ascii_uppercase

    #Prefix
    prefix = name + '_'

    #create linear plane
    basePlane = mc.nurbsPlane(
        p=(0, 0, 0),
        ax=(0, 1, 0),
        width=1,
        lengthRatio=1,
        d=1,
        u=1,
        v=1,
        ch=0,
        n=prefix + 'originator_nPlane'
    )[0]

    #Slide plane so the edge is the origin of the world
    mc.move(0, 0, 0, basePlane + '.cv[0][0]', worldSpace=True)
    mc.move(height, 0, 0, basePlane + '.cv[1][0]', worldSpace=True)
    mc.move(0, 0, width, basePlane + '.cv[0][1]', worldSpace=True)
    mc.move(height, 0, width, basePlane + '.cv[1][1]', worldSpace=True)

    botRtP = mc.pointPosition(basePlane + '.cv[0][0]')
    botLfP = mc.pointPosition(basePlane + '.cv[1][0]')
    topRtP = mc.pointPosition(basePlane + '.cv[0][1]')
    topLfP = mc.pointPosition(basePlane + '.cv[1][1]')

    if direction == 'v':
        mc.reverseSurface(basePlane, d=3, ch=0, rpo=1)

        densityU = lyrDensityV
        densityV = lyrDensityU

    else:
        densityU = lyrDensityU
        densityV = lyrDensityV

    '''Basic grps'''
    #Create basic grps
    topGrp = prefix + 'rig_grp'
    if not mc.objExists(topGrp):
        topGrp = mc.createNode('transform', n=topGrp)

    #Create connection top grp
    connectionLayerNode = prefix + 'connectionLayer'
    if not mc.objExists(connectionLayerNode):
        connectionLayerNode = mc.createNode('transform', n=connectionLayerNode)

    mc.parent(connectionLayerNode, topGrp)

    ##### RUN function createNormPlane to list of surfaces names
    sAttributeName = 'origLayerPlane'
    layerGeos, surfGrp = createNormPlane(prefix, '', basePlane, numLayers, surfLyr, densityU, densityV,
                                         connectionLayerNode, sAttributeName)

    #Create connection top grp
    driverSurfacesGrp = mc.createNode('transform', n=prefix + 'driver_surfaces_grp')
    mc.setAttr(driverSurfacesGrp + '.v', 0, lock=True)

    driverSurfaceList = []

    for i in range(0, numLayers):
        #get the final outpyt surfaces with the same resolution
        driverSurface = mc.duplicate(layerGeos[-1], n='%s_%s_driver'%(layerGeos[-1], LETTERS[i]))[0]
        mc.parent(driverSurface, driverSurfacesGrp)
        driverSurfaceList.append(driverSurface)


    #add follicles
    allFol, cvTags, allLyrJointList, folTopGrp, follicleGrpList, allListOfCtrlsList = addFolliclesToAll(prefix, '', numLayers, surfLyr,
                                                                                    layerGeos, connectionLayerNode,
                                                                                    True, '', rotationOn, oneDimension, driverSurfaceList,
                                                                                    direction)

    #Create base surface
    baseSurf = mc.duplicate(layerGeos[-1], n='%sbase_surf'%prefix)[0]

    '''def'''
    #def
    #Deform layerGeos to generate weitghts on the driver surface
    layerGeos, driverSurfaceList, surfLyr, allListOfCtrlsList

    #move ctrls and mesure distance

    #create blendshape to next surf
    blnd = mc.blendShape(baseSurf, driverSurfaceList[0], frontOfChain=True, n=prefix + 'base_blnd')[0]
    targets = mc.listAttr(blnd + '.w', m=1)
    mc.setAttr(blnd + '.' + targets[0], 1, lock=1)

    for x in range(0, numLayers-1):
        wrapSurf = layerGeos[x]
        wrapped = mc.duplicate(driverSurfaceList[x], n = driverSurfaceList[x] + '_TMP')[0]

        mc.select(wrapped, wrapSurf, r=True)
        mel.eval('CreateWrap ;')

        bindJs = allListOfCtrlsList[x]

        cvs = mc.ls(wrapped + '.cv[*][*]', fl=1)

        allDisplacement = []
        #j = bindJs[0]
        for j in bindJs:

            pos = mc.xform(j, q=1, ws=1, rp=1)

            displacement = []
            #v = vtxSmoothed[0]
            for v in cvs:
                #get initial pos
                iniPos = mc.pointPosition(v, world=1)


                #get deformed pos
                mc.move(0, -1, 0, j, relative=1)
                defPos = mc.pointPosition(v, world=1)

                #get distance between them
                iniPosV = om.MVector(iniPos[0], iniPos[1], iniPos[2])
                defPosV = om.MVector(defPos[0], defPos[1], defPos[2])

                resultV = defPosV - iniPosV

                length = resultV.length()
                displacement.append(length)

                mc.move(0, 1, 0, j, relative=1)

            allDisplacement.append(displacement)

        mc.delete(wrapped)

        #Create blnd skinned
        #blndSkndSurf = mc.duplicate(driverSurfaceList[x], n = driverSurfaceList[x].replace('driver', 'blndSkndSurf'))[0]
        blndSkndSurf = driverSurfaceList[x+1]

        #create blendshape to next surf
        blnd = mc.blendShape(driverSurfaceList[x], driverSurfaceList[x+1], frontOfChain=True, n='layer_%s_blnd'%LETTERS[x])[0]
        targets = mc.listAttr(blnd + '.w', m=1)
        mc.setAttr(blnd + '.' + targets[0], 1, lock=1)

        #skin ctrls on driverSurfaceList[x]
        outSkin = mc.skinCluster( bindJs, blndSkndSurf, dr=4.5, maximumInfluences=1, frontOfChain=0, toSelectedBones=1, n = 'outMesh_skC')

        #set weights
        for i, j in enumerate(bindJs):
            for y, dis in enumerate(allDisplacement[i]):
                normValue = dis
                mc.skinPercent(outSkin[0], blndSkndSurf + '.' + cvs[y].split('.')[1], transformValue=[(j, normValue)])
                mc.setAttr(j + '.liw', 1)

        #Connect prebindMatrix
        mc.select('%s.cv[*:*]' % (blndSkndSurf), r=1)
        cvs = mc.ls(sl=1, fl=1)

        if outSkin:
            for i in range(len(bindJs)):
                if mc.attributeQuery('parentMatrixPath', node=bindJs[i], exists=True):
                    mtxJnt = mc.listConnections(bindJs[i] + '.parentMatrixPath')
                    mc.connectAttr('%s.parentInverseMatrix' % mtxJnt[0], outSkin[0] + '.bindPreMatrix[%d]' % i)
                else:
                    mc.connectAttr('%s.parentInverseMatrix' % bindJs[i], outSkin[0] + '.bindPreMatrix[%d]' % i)


    mc.parent(baseSurf, driverSurfacesGrp)
    mc.parent(driverSurfacesGrp, folTopGrp, topGrp)
    mc.delete(surfGrp, basePlane)


    return topGrp, follicleGrpList[0], allLyrJointList[0], allLyrJointList[1], connectionLayerNode, allListOfCtrlsList, baseSurf, driverSurfaceList




def createNormPlane(prefix,
                    driven,
                    basePlane,
                    numLayers,
                    surfLyr,
                    densityU,
                    densityV,
                    connectionLayerNode,
                    sAttributeName):
    #return list with surf names
    layerSurfaces = []
    #layerNum = 1 #tmp
    #Create conlyr
    conlyr = mc.createNode('transform', n=prefix + 'surfaces_connectionLayer' + driven)
    mc.parent(conlyr, connectionLayerNode)

    #Create sufaces parent
    surfGrp = mc.createNode('transform', n=prefix + 'surfaces_grp' + driven)

    for layerNum in range(1, numLayers + 1):

        lyrTag = surfLyr[layerNum - 1]

        #plane name and
        surface = prefix + 'plane_' + lyrTag + '_surf' + driven
        surface = mc.duplicate(basePlane, n=surface)[0]
        mc.parent(surface, surfGrp)
        layerSurfaces.append(surface)
        #Add message attr
        connectMessageAttr(conlyr, surface, sAttributeName)

        #num of spans
        spansU = densityU[layerNum - 1]
        spansV = densityV[layerNum - 1]

        #misc
        rebuildType = 0
        degreeU = 1
        degreeV = 1

        #Create linear first to get the right spacing
        mc.rebuildSurface(
            surface,
            constructionHistory=0,
            replaceOriginal=1,
            rebuildType=rebuildType,
            endKnots=1,
            keepRange=0,
            keepControlPoints=0,
            keepCorners=0,
            spansU=spansU,
            degreeU=degreeU,
            spansV=spansV,
            degreeV=degreeV,
            tolerance=0,
            fitRebuild=0,
            direction=2
        )
        #Rebuild it to quadratic maintaining cvs pos
        #Check if lyr A is linear
        if spansU != 1:
            degreeU = 2
        if spansV != 1:
            degreeV = 2

        mc.rebuildSurface(
            surface,
            constructionHistory=0,
            replaceOriginal=1,
            rebuildType=rebuildType,
            endKnots=1,
            keepRange=0,
            keepControlPoints=1,
            keepCorners=0,
            spansU=spansU,
            degreeU=degreeU,
            spansV=spansV,
            degreeV=degreeV,
            tolerance=0,
            fitRebuild=0,
            direction=2
        )

    #mc.delete(basePlane)

    return (layerSurfaces, surfGrp)


#All secondary functions

#Get cv numbers into an unsable strig for all names
def getCvColRow(cv):
    #get name colunms and rows from cv name
    cvNum = cv.split('.cv')[-1]
    cvNum = cvNum.split('][')
    #add col and row with padding
    row = cvNum[0][1:].rjust(2, '0')
    col = cvNum[1][:-1].rjust(2, '0')
    return [row, col]


#Create layer with attributes connection.
def connectMessageAttr(lyrGrp, object, sAttributeName):
    sAttributeType = "message"

    if not type(object) == type(list()):
        mc.addAttr(object, longName=sAttributeName, attributeType=sAttributeType)
        #Connect default message attr from "layer" group node to
        mc.connectAttr(lyrGrp + '.message', object + '.' + sAttributeName)
    else:
        for obj in object:
            # Attribute type
            #Add attr type message to object
            mc.addAttr(obj, longName=sAttributeName, attributeType=sAttributeType)
            #Connect default message attr from "layer" group node to
            mc.connectAttr(lyrGrp + '.message', obj + '.' + sAttributeName)


def follicleFromCvs(prefix, driven, currentLyrGeo, lyrCvs, tag, rotationOn):
    cvTagNumList = []
    follicleList = []

    for p in lyrCvs:

        #get name colunms and rows from cv name function
        rowCol = getCvColRow(p)

        name = prefix + 'layer_' + tag + '_' + rowCol[0] + '_' + rowCol[1]
        #if

        cvTagNumList.append(tag + '_' + rowCol[0] + '_' + rowCol[1])

        #Create follicle grp
        folP = prefix + 'follicles_' + tag + '_grp' + driven
        if not (mc.objExists(folP)):
            folP = mc.createNode('transform', n=folP)

        #Create follicle transform and shape
        fol = mc.createNode('transform', n=name + '_follicle_n' + driven, p=folP)
        follicleList.append(fol)
        fols = mc.createNode('follicle', p=fol, n=name + '_follicleShape' + driven)
        #hide shape
        mc.setAttr(fols + '.v', 0, lock=True)

        #Connect to currentLyrGeo
        mc.connectAttr(currentLyrGeo + '.worldMatrix[0]', fols + '.inputWorldMatrix')
        mc.connectAttr(currentLyrGeo + '.local', fols + '.inputSurface')
        mc.connectAttr(fols + '.outTranslate', fol + '.translate')

        #connect rotation if needed
        if rotationOn:
            mc.connectAttr(fols + '.outRotate', fol + '.rotate')

        #Create loc on point
        pos = mc.xform(p, q=1, t=1, ws=1)
        loc = mc.spaceLocator(n='pos_loc')[0]
        mc.move(pos[0], pos[1], pos[2], loc, rpr=1)
        mc.parent(loc, currentLyrGeo)

        uRng = mc.getAttr(currentLyrGeo + '.minMaxRangeU')
        vRng = mc.getAttr(currentLyrGeo + '.minMaxRangeV')

        #Create node closestPointOnSurface
        pointSurf = mc.createNode('closestPointOnSurface', n='tmp_closestPointOnSurface_1')
        mc.connectAttr(currentLyrGeo + '.local', pointSurf + '.inputSurface')
        mc.connectAttr(loc + '.translate', pointSurf + '.inPosition')

        #Get uv coords
        u = mc.getAttr(pointSurf + '.u')
        v = mc.getAttr(pointSurf + '.v')

        #Normalized uv's then set follicle paramenters
        normU = abs(u / uRng[0][1])
        normV = abs(v / vRng[0][1])

        mc.setAttr(fols + '.parameterU', normU)
        mc.setAttr(fols + '.parameterV', normV)

        mc.delete(pointSurf, loc)

    return (follicleList, cvTagNumList, folP)


def follicleFromCvsOneD(prefix, driven, currentLyrGeo, lyrCvs, tag, rotationOn, direction):
    cvTagNumList = []
    follicleList = []

    for p in lyrCvs:

        #get name colunms and rows from cv name function
        if direction == 'u':
            rowCol = getCvColRow(p)
        else:
            tmpRowCol = getCvColRow(p)
            rowCol = [tmpRowCol[1], tmpRowCol[0]]



        if rowCol[1] == '00':
            name = prefix + 'layer_' + tag + '_' + rowCol[0]

            cvTagNumList.append(tag + '_' + rowCol[0])

            #Create follicle grp
            folP = prefix + 'follicles_' + tag + '_grp' + driven
            if not (mc.objExists(folP)):
                folP = mc.createNode('transform', n=folP)

            #Create follicle transform and shape
            fol = mc.createNode('transform', n=name + '_follicle_n' + driven, p=folP)
            follicleList.append(fol)
            fols = mc.createNode('follicle', p=fol, n=name + '_follicleShape' + driven)
            #hide shape
            mc.setAttr(fols + '.v', 0, lock=True)

            #Connect to currentLyrGeo
            mc.connectAttr(currentLyrGeo + '.worldMatrix[0]', fols + '.inputWorldMatrix')
            mc.connectAttr(currentLyrGeo + '.local', fols + '.inputSurface')
            mc.connectAttr(fols + '.outTranslate', fol + '.translate')

            #connect rotation if needed
            if rotationOn:
                mc.connectAttr(fols + '.outRotate', fol + '.rotate')

            #Create loc on point
            pos = mc.xform(p, q=1, t=1, ws=1)
            loc = mc.spaceLocator(n='pos_loc')[0]
            mc.move(pos[0], pos[1], pos[2], loc, rpr=1)
            mc.parent(loc, currentLyrGeo)

            uRng = mc.getAttr(currentLyrGeo + '.minMaxRangeU')
            vRng = mc.getAttr(currentLyrGeo + '.minMaxRangeV')

            #Create node closestPointOnSurface
            pointSurf = mc.createNode('closestPointOnSurface', n='tmp_closestPointOnSurface_1')
            mc.connectAttr(currentLyrGeo + '.local', pointSurf + '.inputSurface')
            mc.connectAttr(loc + '.translate', pointSurf + '.inPosition')

            #Get uv coords
            u = mc.getAttr(pointSurf + '.u')
            v = mc.getAttr(pointSurf + '.v')

            #Normalized uv's then set follicle paramenters
            normU = abs(u / uRng[0][1])
            normV = abs(v / vRng[0][1])


            if direction == 'v':
                mc.setAttr(fols + '.parameterV', normV)
                mc.setAttr(fols + '.parameterU', .5)
            else:
                mc.setAttr(fols + '.parameterU', normU)
                mc.setAttr(fols + '.parameterV', .5)

            mc.delete(pointSurf, loc)

    return (follicleList, cvTagNumList, folP)


def jointToFollicle(prefix, driven, follicleList, tag, radius, lyrTag, connectionLayerNode):
    jointList = []
    x = 0

    jointConnectionLyr = mc.createNode('transform', n=prefix + 'joint_' + lyrTag + '_connectionLayer' + driven)
    mc.parent(jointConnectionLyr, connectionLayerNode)


    #j = follicleList[0]
    for s in follicleList:
        #name = prefix + 'lyr_' + tag[x] + '_ctrl' + driven
        name = prefix + tag[x] + '_ctrl' + driven
        x = x + 1
        mc.select(cl=1)
        j = mc.joint(n=name, radius=radius)
        jointList.append(j)
        #Add connectMessageAttr(lyrGrp, object, sAttributeName)
        sAttributeName = name
        connectMessageAttr(jointConnectionLyr, j, sAttributeName)

        mc.select(cl=1)
        mc.parent(j, s)
        mc.setAttr(j + '.tx', 0)
        mc.setAttr(j + '.ty', 0)
        mc.setAttr(j + '.tz', 0)

        mc.setAttr(j + '.jointOrientX', 0)
        mc.setAttr(j + '.jointOrientY', 0)
        mc.setAttr(j + '.jointOrientZ', 0)

    return jointList


#Loop thru every surface to add follicles
def addFolliclesToAll(prefix, driven, numLayers, surfLyr, layerGeos, connectionLayerNode, skinBind, singleSurf,
                      rotationOn, oneDimension, driverSurfaceList, direction):
    #TEST for loop
    allFollicles = []
    cvTagNum = []
    radius = .7
    allLyrJointList = []
    follicleGrpList = []
    allListOfCtrlsList = []


    #follicles top grp
    folTopGrp = mc.createNode('transform', n=prefix + 'follicles_top_grp' + driven)

    for i in range(0, numLayers):

        #Test if it's not the last surface, if it is break
        '''if i == numLayers-1:
            mc.warning('Breaking HERE : ' + layerGeos[i])
            break'''

        #get current layer surface
        currentLyrGeo = driverSurfaceList[i]
        nextLyrGeo = layerGeos[i]

        # Check if all follicles should be in the same surface
        if singleSurf:
            currentLyrGeo = singleSurf

        #get points from next surface
        lyrCvs = mc.ls(nextLyrGeo + '.cv[*][*]', fl=1)

        #get Tag
        lyrTag = surfLyr[i]

        ##### Run follicleFromCvs function to create the follicles

        if oneDimension:
            folliclesList, cvNameList, folP = follicleFromCvsOneD(prefix, driven, currentLyrGeo, lyrCvs, lyrTag,
                                                                  rotationOn, direction)
            mc.parent(folP, folTopGrp)
            follicleGrpList.append(folP)

            allFollicles.append(folliclesList)
            cvTagNum.append(cvNameList)

        else:
            folliclesList, cvNameList, folP = follicleFromCvs(prefix, driven, currentLyrGeo, lyrCvs, lyrTag, rotationOn)
            mc.parent(folP, folTopGrp)

            follicleGrpList.append(folP)

            allFollicles.append(folliclesList)
            cvTagNum.append(cvNameList)

            ##### Create joint in each follicle
        lyrJointList = jointToFollicle(prefix, driven, folliclesList, cvNameList, radius, lyrTag, connectionLayerNode)
        allLyrJointList.extend(lyrJointList)
        allListOfCtrlsList.append(lyrJointList)

        radius = radius / 1.7

        #bind
        if skinBind == True:
            skin = mc.skinCluster(lyrJointList, nextLyrGeo, dr=4.5, maximumInfluences=1, frontOfChain=1,
                                  toSelectedBones=1, n=prefix + 'layer_' + lyrTag + '_skC')

    return allFollicles, cvTagNum, allLyrJointList, folTopGrp, follicleGrpList, allListOfCtrlsList




############################################################################################################################################
#Panrent Shape
############################################################################################################################################

def parentShapeRibbon(inShapeObj, inTarget, maintainPos=False):
    '''
    Description:
        Panrent shape nodes to target objects.
        Dependencies:
            NONE
    '''
    mc.parent(inShapeObj, inTarget)
    mc.makeIdentity(inShapeObj, apply=maintainPos, t=True, r=True, s=True)
    mc.parent(inShapeObj, w=True)

    shapes = []

    for s in mc.listRelatives (inShapeObj, shapes=True):
        newShape = mc.rename(s, inTarget + 'Shape_1')
        shapes.append(newShape)
    mc.parent(shapes, inTarget, r=True, s=True)

    #Delete old grp
    mc.delete(inShapeObj)





def delShapes(inTransform):
    shapes = mc.listRelatives(inTransform, s=True)
    if shapes:
        for s in shapes:
            mc.delete(s)
############################################################################################################################################
#Panrent Shape
############################################################################################################################################

def parentShape(inShapeObj, inTarget, maintainPos=False):
    '''
    Description:
        Panrent shape nodes to target objects.
        Dependencies:
            NONE
    '''
    mc.parent(inShapeObj, inTarget)
    mc.makeIdentity(inShapeObj, apply=maintainPos, t=True, r=True, s=True)
    mc.parent(inShapeObj, w=True)

    shapes = []

    for s in mc.listRelatives (inShapeObj, shapes=True):
        newShape = mc.rename(s, inTarget + 'Shape_1')
        shapes.append(newShape)
    mc.parent(shapes, inTarget, r=True, s=True)

    #Delete old grp
    mc.delete(inShapeObj)








#################################################################################################################################
#  NOT DONE - addCtrlShapesToRibbon - WIP - Not implemented yet
############################################################################################################################################



#Spine
def addCtrlShapesToRibbon(
                          inControlLists,
                          overallScale=1.0,
                          scale=[(0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3)],
                          color=[13, 7, 12, 26, 13, 7, 12, 26, 13]
                          ):
    '''
    Description:
        This is made to be use with the module fs_ribbon. It will add curve shapes to ribbon
        control joints.
        Dependencies:
            -parentShape()
            -createCtrlShapes as ccCreate
        Example:
            Run createRibbon() then get the list of controls and run addCtrlShapesToRibbon:
                sl = fsRbn.createRibbon()[5]
                attachBendToJoint(sl[0], sl[1], 'inNames')
    '''

    #add curver to controls
    for i, layer in enumerate(inControlLists):
        for j in layer:
            if j:

                if i==0:
                    shpCtrl = ccs.circleCompass(orientation=(0, 0,90), scale=(.2 * scale[i][0] * overallScale, .2 * scale[0][1] * overallScale, .2 * scale[0][2] * overallScale), color=color[0])
                elif i==1:
                    shpCtrl = ccs.circleX(orientation=(0, 0,90), scale=(.326 * scale[i][0] * overallScale, .326 * scale[i][1] * overallScale, .326 * scale[i][2] * overallScale), color=color[1])
                elif i==2:
                    shpCtrl = ccs.doubleNail(orientation=(0, 0,90), scale=(scale[i][0] * .1 * overallScale, scale[i][1] * .1 * overallScale, scale[i][2] * .1 * overallScale), color=color[2])

                elif i==3:
                    shpCtrl = ccs.prism(scale=(.08 * overallScale, .03 * overallScale, .08 * overallScale), orientation=(0, 0,90), color=color[3])
                else:
                    shpCtrl = ccs.cube(scale=(.03 * overallScale, .03 * overallScale, .03 * overallScale), color=color[4])

                delShapes(j)
                parentShape(shpCtrl, j)


def addCtrlShapesToRibbonII(
                          inControlLists,
                          overallScale=1.0,
                          scale=[(0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3)],
                          color=[13, 7, 12, 26, 13]
                          ):
    '''
    Description:
        This is made to be use with the module fs_ribbon. It will add curve shapes to ribbon
        control joints.
        Dependencies:
            -parentShape()
            -createCtrlShapes as ccCreate
        Example:
            Run createRibbon() then get the list of controls and run addCtrlShapesToRibbon:
                sl = fsRbn.createRibbon()[5]
                attachBendToJoint(sl[0], sl[1], 'inNames')
    '''

    #add curver to controls
    for i, layer in enumerate(inControlLists):
        for j in layer:
            if j:

                if i==0:
                    shpCtrl = ccs.doubleNail(orientation=(0, 0,90), scale=(.2 * scale[i][0] * overallScale, .2 * scale[0][1] * overallScale, .2 * scale[0][2] * overallScale), color=color[0])
                elif i==1:
                    shpCtrl = ccs.doubleNail(orientation=(0, 0,90), scale=(.326 * scale[i][0] * overallScale, .326 * scale[i][1] * overallScale, .326 * scale[i][2] * overallScale), color=color[1])
                elif i==2:
                    shpCtrl = ccs.doubleNail(orientation=(0, 0,90), scale=(scale[i][0] * .1 * overallScale, scale[i][1] * .1 * overallScale, scale[i][2] * .1 * overallScale), color=color[2])

                elif i==3:
                    shpCtrl = ccs.prism(scale=(.08 * overallScale, .03 * overallScale, .08 * overallScale), orientation=(0, 0,90), color=color[3])
                else:
                    shpCtrl = ccs.cube(scale=(.03 * overallScale, .03 * overallScale, .03 * overallScale), color=color[4])

                delShapes(j)
                parentShape(shpCtrl, j)


def addCtrlShapesToRibbonIII(
                          inControlLists,
                          controlTypeList=['circleCross', 'cube', 'squareCross'],
                          overallScale=1.0,
                          scale=[(0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3)],
                          color=[13, 7, 12, 26, 13],
                          orientationList=[(0, 0,90), (0, 0,90), (0, 0,90), (0, 0,90), (0, 0,90), (0, 0,90)]
                          ):
    '''
    Description:
        This is made to be use with the module fs_ribbon. It will add curve shapes to ribbon
        control joints.
        Dependencies:
            -parentShape()
            -createCtrlShapes as ccCreate
        Example:
            Run createRibbon() then get the list of controls and run addCtrlShapesToRibbon:
                sl = fsRbn.createRibbon()[5]
                attachBendToJoint(sl[0], sl[1], 'inNames')
    '''

    #add curver to controls
    for i, layer in enumerate(inControlLists):
        for j in layer:

            if j:

                if not controlTypeList[i]:
                        controlType = 'cube'
                else:
                    controlType = controlTypeList[i]

                if not orientationList[i]:
                        orientation = (0, 0,90)
                else:
                    orientation = orientationList[i]

                #Create shapes
                shpCtrl = eval('ccs.' + controlType + '(orientation=' + str(orientation) + ', scale=(.2 * scale[i][0] * overallScale, .2 * scale[i][1] * overallScale, .2 * scale[i][2] * overallScale), color=color[i])')

                delShapes(j)
                parentShape(shpCtrl, j)




def reShapeRibbon(inShaperSurf, prefix='rbn'):

    inShaperSurf = mc.ls(sl=1)[0]
    prefix = 'wing_r_rb'

    shape = mc.listRelatives(inShaperSurf, shapes=True)[0]
    spansU, spansV = mc.getAttr('%s.spansUV'%shape)[0]


    spansU, spansV = mc.getAttr('%s.spansUV'%shape)[0]

    returnList = createRibbon(width=10.553, height=1.013, densityU=(3, spansU + 1), numLayers=2, autoCtrlCurves=1, name=prefix)

    driverSurf = returnList[6]
    controlLists = returnList[5]
    #weight=[0,1.0]
    blnd = mc.blendShape(inShaperSurf, driverSurf, origin='world', n='tmp_blnd', weight=[0,1.0])[0]
    #Set it on
    #targets = mc.listAttr(blnd + '.w', m=1)

    #mc.setAttr(blnd + '.' + targets[0], 1, lock=1)

    mc.delete(driverSurf, ch=1)



    #Spine
    #Run it
    sA = .4
    sB = .2
    sC = 0.75
    addCtrlShapesToRibbon(
                              controlLists,
                              overallScale=6.1,
                              scale=[(sA, sA, sA), (sB, sB, sB), (sC, sC, sC), (0.3, 0.3, 0.3)],
                              color=[13, 17, 25, 26, 13]
                              )
