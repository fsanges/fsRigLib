'''
Copyright MIT 2013
Author: Felipe Sanges

About: Personal library of maya rigging helpers

Usage:
    Use docstrings to get help for each function:
        mc.warning(createCurveInSurfaceCenter.__doc__)
        or
        help(createCurveInSurfaceCenter)
'''

import maya.cmds as mc
import math
import maya.OpenMaya as om
import maya.mel as mel
import pymel.core as pm

import controlCurveShapes as ccs



#######################################################################################################
''' Wire to SkinCluster 08/05/2017 ''' #########################################################
#######################################################################################################

def wire_to_skinCluster(curve, geo, name="", jntList="", dropoffDistance=100, rotation=0.00):
    """
        Date : 08/05/2017
        Author : Felipe Sanges
        Usage :
        curve, geo = mc.ls(sl=1)
        rlx.wire_to_skinCluster(curve, geo, name='name', dropoffDistance=100, rotation=0.00)
        """
    skinGeo = mc.duplicate(geo, n=geo + '_skin')[0]
    if not name:
        name = 'tmp'
    curveTPos = mc.xform(curve + ".cv[*]", q=1, ws=True, t=1)
    posList = zip(curveTPos[::3], curveTPos[1::3], curveTPos[2::3])
    
    if not jntList:
        jntList = list()
        for i, pos in enumerate(posList):
            grp = create_grp(name='%s_grp'%name)
            mc.select(cl=True)
            jnt = mc.joint(p=pos, name='%s_%02d_jnt'%(name, i ))
            jntList.append(jnt)
        mc.parent(jntList, grp)

    #--- Skin Curve
    crv_skin = mc.skinCluster( jntList, curve, dr=4.5, maximumInfluences=1, frontOfChain=1, toSelectedBones=1, n = 'layer_A_skC')
    wire = mc.wire(geo, gw=False, en=1.000000, ce=0.000000, li=0.000000, w=curve )[0]

#--- Set wire attrs
mc.setAttr(wire + ".rotation", rotation)
    mc.setAttr(wire + ".dropoffDistance[0]", dropoffDistance)
    
    #--- Get all vertices
    vtxGeo = mc.ls(geo + '.vtx[*]', fl=1)
    
    #   Get displacement from all vertices
    allDisplacement = []
    
    for j in jntList:
        
        displacement = []
        for v in vtxGeo:
            #   get initial pos
            iniPos = mc.pointPosition(v, world=1)
            
            #   get deformed pos
            mc.move(0, -1, 0, j, relative=1)
            defPos = mc.pointPosition(v, world=1)
            
            #   get distance between them by subtracting the two vectors
            iniPosV = om.MVector(iniPos[0], iniPos[1], iniPos[2])
            defPosV = om.MVector(defPos[0], defPos[1], defPos[2])
            
            resultV = defPosV - iniPosV
            
            #   The final length of the vector is the actual final weight value already normalized
            length = resultV.length()
            displacement.append(length)
            
            mc.move(0, 1, 0, j, relative=1)
        
        allDisplacement.append(displacement)
    mc.warning('DONE!!')

#  skin
mc.setAttr(wire + ".envelope", 0)
    outSkin = mc.skinCluster( jntList, geo, dr=4.5, maximumInfluences=1, frontOfChain=1, toSelectedBones=1, n = 'outMesh_skC')
    
    for i, j in enumerate(jntList):
        for x, dis in enumerate(allDisplacement[i]):
            mc.skinPercent(outSkin[0], geo + '.vtx[' + str(x) + ']', transformValue=[(j, dis)])
            
            #Lock influence weights
            mc.setAttr(j + '.liw', 1)

mc.warning('Done')
    mc.delete(wire)
    return jntList




#######################################################################################################
''' FK Simple Setup 08/06/2017 ''' #########################################################
#######################################################################################################

def fk_simple_setup(inJointList, 
                    inSuffix='Jnt', 
                    outSuffix='Ctrl', 
                    fkSuffix='Fk', 
                    overallScale=1.0, 
                    shapeFK='circleCompass', 
                    shapeFKScale=(1.2, 1.2, 1.2), 
                    shapeChild='circleX', 
                    shapeChildScale=(1, 1, 1),
                    fkColor=23,
                    childColor=26,
                    useShapesFromScene=False
                    ):
    ''' FK Simple Setup Help :
        Creates a simple fk setup with shapes
        08/06/2017 
        Usage : 
            shapeFK = ccs.cube(color=23)
            shapeChild = ccs.sphere(color=26)
            fkBind = rlx.fk_simple_setup(fkRbList, 
                                inSuffix='Jnt', 
                                outSuffix='Ctrl', 
                                fkSuffix='Fk', 
                                overallScale=2.0, 
                                shapeFK=shapeFK, 
                                shapeChild=shapeChild, 
                                fkColor=23,
                                childColor=26,
                                useShapesFromScene=1) '''
    # --- Rename chain
    fkList = list()
    bindList = list()
    for s in inJointList:

        if inSuffix in s:
            fk = s.replace(inSuffix, fkSuffix)
            trs = s.replace(inSuffix, outSuffix)
        else:
            fk = '%s_%s_%s'%(s, fkSuffix, outSuffix)
            trs = s + '_' +  outSuffix

        fk = mc.duplicate(s, po=1, n=fk)[0]
        trs = mc.duplicate(s, po=1, n=trs)[0]
        bindList.append(trs)

        mc.parent(fk, s)
        mc.parent(trs, fk)

        if fkList:
            mc.parent(s, fkList[-1])
        fkList.append(fk)

        finalScaleFk = [a * b for a, b in zip(shapeFKScale, (overallScale, overallScale, overallScale))]
        finalScaleChld = [a * b for a, b in zip(shapeChildScale, (overallScale, overallScale, overallScale))]

        if useShapesFromScene:
            if mc.objExists(shapeFK) and mc.objExists(shapeChild):
                fkCtrl = mc.duplicate(shapeFK, renameChildren=True)[0]
                ctrl = mc.duplicate(shapeChild, renameChildren=True)[0]
            else:
                mc.warning(shapeFK)
                mc.warning(shapeChild)
                mc.error('Flag "useShapesFromScene" is set to true. I this case you need to make sure the shapeFK and shapeChild have existing objects!')
        else:
            fkCtrl = eval('ccs.%s(orientation = (0, 0, 90), scale=%s, color=%s)'%(shapeFK, finalScaleFk, fkColor))
            ctrl = eval('ccs.%s(orientation = (0, 0, 90), scale=%s, color=%s)'%(shapeChild, finalScaleChld, childColor))
        
        parentShape(fkCtrl, fk)
        parentShape(ctrl, trs)

        if s == inJointList[-1]:
            mc.parent(trs, s)
            mc.delete(fk)
    
    return bindList




#######################################################################################################
''' Joints to Driver Mesh 16/04/2017 ''' #########################################################
#######################################################################################################

def joints_to_driver_mesh(inJointList, scale = 0.1, name='tmp'):
    ''' 
    Creates a poly face for each inJoints and set up follicles on the combined mesh. 
    OBS : Mirroed joints should create symmetrical meshes, but not sym behavior.
    Usage : 
    inJointList = mc.ls(sl=1, type='joint')
    res = rlx.joints_to_driver_mesh(inJointList, scale = 0.1, name='tmp')
    '''
    
    #    Place joints using z as your normal for the face mesh
    faceScale = scale
    jntNum = len(inJointList)
    if jntNum < 2:
        #mc.error("Select two or more joints.")
        mc.warning('One joint selected, creating a single facet mesh for joint.')

    faceList = list()
    for i, jnt in enumerate(inJointList):
        scale = faceScale
        #face = mel.eval("polyCreateFacet -ch 0 -tx 1 -s 1 -p -0.5 0 -0.5 -p 0.5 0 -0.5 -p 0.5 0 0.5 -p -0.5 0 0.5 ;")[0]
        facePointPosList = [(-0.5, 0.0, -0.5), (0.5, 0.0, -0.5), (0.5, 0.0, 0.5), (-0.5, 0.0, 0.5)]
        face = mc.polyCreateFacet(ch=0, p=facePointPosList)[0]
        faceList.append(face)
        mc.scale(faceScale, faceScale, faceScale, face, pivot=(0, 0, 0), absolute=True )
        mc.makeIdentity(face, apply=True, s=1)

        #  Scale uv
        #  Find num of grid colums/lines
        sqrtJntNum = math.sqrt( jntNum )
        gridNum = int(math.ceil(sqrtJntNum))

        scaleUV = 1.0/gridNum
        mc.polyEditUV(face + '.map[*]',  pu=0, pv=0, scaleU=scaleUV, scaleV=scaleUV)

    if not jntNum < 2:
        #  Fill uv space with square uvs by just scaling and moving each in a grid
        #  Find u and v values for each poly uvs new pos
        line = gridNum
        m=0
        lnColList = list()
        for n in range(int(math.pow(gridNum, 2))):
            if n == jntNum+1:
                break
            if not n < line:
                line = gridNum + line

            curline = line/gridNum
            lnColList.append([curline-1, m])
            
            m=m+1
            if m==gridNum:
                m=0

        #   Apply uv positions
        for i, poly in enumerate(faceList):#pass
            ln, col = lnColList[i]
            mc.polyEditUV(faceList[i] + '.map[*]', u=scaleUV*ln, v=scaleUV*col)

        #   Place polys in world space
        for face, jnt in zip(faceList, inJointList):
            mc.parent(face, jnt)
            mc.makeIdentity(face, apply=False, t=1, r=1, s=1)
            mc.parent(face, w=1)

        #   Combine all
        mesh = mc.polyUnite(faceList, ch=0, mergeUVSets=1, centerPivot=1, name=name)[0]
    else:
        mesh = face

    #   Get Shape
    shape = mc.listRelatives(mesh, s=1)[0]
    #   Create follicle for each joint
    folList = list()
    bindJList = list()
    for i, jnt in enumerate(inJointList):#pass
        #for i, vc in enumerate(triLocList):
        #Create cpom
        cpom = mc.createNode('closestPointOnMesh', n='tmp_cpom')
        mc.connectAttr(shape+'.worldMesh[0]',cpom+'.inMesh')
        mc.connectAttr(jnt + '.translate',cpom+'.inPosition', f=1)

        parameterU = mc.getAttr('%s.parameterU'%cpom)
        parameterV = mc.getAttr('%s.parameterV'%cpom)

        #Create follicle transform and shape
        fols = mc.createNode('follicle', n = "%s_%s_follicle_nodeShape"%(jnt, i)) #, n = mesh('mesh', 'follicle_nodeShape'), p = fol )
        fol = mc.listRelatives(fols, p=1)[0]
        #   Set uv values
        if jntNum < 2:
            parameterU = .5
            parameterV = .5
        mc.setAttr('%s.parameterU'%fols, parameterU)
        mc.setAttr('%s.parameterV'%fols, parameterV)
        #   Hide follicle
        mc.setAttr('%s.v'%fols, 0, lock=True)
        #   Connect to mesh
        mc.connectAttr(shape + '.worldMatrix[0]', fols + '.inputWorldMatrix')
        mc.connectAttr(shape + '.outMesh', fols + '.inputMesh')# check for worldMesh[0]
        mc.connectAttr(fols + '.outTranslate', fol + '.translate')
        mc.connectAttr(fols + '.outRotate', fol + '.rotate')

        #Create follicle grp
        folP = '%s_follicles_grp'%mesh
        if not(mc.objExists(folP)):
            folP = mc.createNode('transform', n=folP )
        
        #  Parent joint
        dup = mc.duplicate(jnt, po=1)[0]
        mc.parent(dup, fol)
        mc.parent(fol, folP)

        #   Zero all
        mc.xform(dup, t=(0, 0, 0), ro=(0, 0, 0), s=(1, 1, 1))
        mc.makeIdentity(dup, jo=1, apply=1)
        mc.parent(dup, w=1)
        
        mc.delete(cpom)

        folList.append(fol)
        bindJList.append(dup)

    #   Bind mesh
    skin = mc.skinCluster( bindJList, mesh, dr=4.5, maximumInfluences=1, frontOfChain=1, toSelectedBones=1, n = mesh + '_skC')[0]
    for oj, bj in zip(inJointList, bindJList):#pass
        mc.parent(bj, oj)
        mc.xform(bj, t=(0, 0, 0), ro=(0, 0, 0), s=(1, 1, 1))
        mc.setAttr(bj + ".jointOrientX", 0)
        mc.setAttr(bj + ".jointOrientY", 0)
        mc.setAttr(bj + ".jointOrientZ", 0)

    #   Delete mesh history
    mc.delete(mesh, ch=1)

    for oj, fol in zip(inJointList, folList):#pass

        mc.parent(oj, fol)
        mc.xform(oj, t=(0, 0, 0), ro=(0, 0, 0), s=(1, 1, 1))
        mc.setAttr(oj + ".jointOrientX", 0)
        mc.setAttr(oj + ".jointOrientY", 0)
        mc.setAttr(oj + ".jointOrientZ", 0)    

    mc.delete(bindJList)

    #   Mirror /toDo
    
    return mesh, folList


#######################################################################################################
''' Create Surface from Joint Chain 06/04/2017 ''' #########################################################
#######################################################################################################

def surface_from_chain(inJointList, width=0.01, name='surface', degree=2, axis='z'):
    ''' Create Surface from Joint Chain 
        Date : 06/04/2017 
        Usage : rlx.surface_from_chain(inJointList, width=0.01, name='surface', degree=2, axis='z')
    '''

    crvAPosList = list()
    crvBPosList = list()

    for i, j in enumerate(inJointList):

        loc = mc.spaceLocator()[0]

        mc.parent(loc, j)
        mc.makeIdentity(loc, t=1, r=1, apply=0)

        eval('mc.move(width, loc, %s=1, localSpace=1)'%axis)
        crvAPosList.append(mc.xform(loc, q=1, rp=1, ws=1))

        eval('mc.move(-width, loc, %s=1, localSpace=1)'%axis)
        crvBPosList.append(mc.xform(loc, q=1, rp=1, ws=1))
        mc.delete(loc)

    crvA = mc.curve(p=crvAPosList)
    crvB = mc.curve(p=crvBPosList)

    loftSrf = mc.loft(crvA, crvB, ch=0, u=1, c=0, ar=0, d=1, ss=1, rn=0, po=0, rsn=True, n=name)
    mc.delete(crvA, crvB)
    
    mc.rebuildSurface(
                  loftSrf,
                  constructionHistory=0,
                  replaceOriginal=1,
                  rebuildType=0,
                  endKnots=1,
                  keepRange=0,
                  keepControlPoints=1,
                  degreeU=degree,
                  degreeV=1
                  )
    mc.select(loftSrf, r=True)

    
    return loftSrf


#######################################################################################################
''' Follicle to Closest Point 05/04/2017 ''' #########################################################
#######################################################################################################

def follicle_to_closest_point(inSurface, inPosList, name='tmp'):
    """ Usage: rlx.follicle_to_closest_point(inSurface, inPosList, name='tmp')
    """

    folList = list()
    
    for i, pos in enumerate(inPosList):
            
        #Create follicle grp
        folP = '%s_follicles_master_grp'%name
        if not(mc.objExists(folP)):
            folP = mc.createNode('transform', n='%s_follicles_master_grp'%name )

        #Create follicle transform and shape
        fol = mc.createNode('transform', n='%s_follicle_%02d_n'%(name, i), p = folP )
        folList .append(fol)
        fols = mc.createNode('follicle', p = fol, n=fol+'Shape' )
        #Connect to inSurface
        mc.connectAttr(inSurface + '.worldMatrix[0]', fols + '.inputWorldMatrix')
        mc.connectAttr(inSurface + '.local', fols + '.inputSurface')
        mc.connectAttr(fols + '.outTranslate', fol + '.translate')
        mc.connectAttr(fols + '.outRotate', fol + '.rotate')

        #Create loc on point
        #pos = mc.xform(p, q=1, sp=1, ws=1)
        loc = mc.spaceLocator(n='pos_loc')[0]
        mc.move(pos[0], pos[1], pos[2], loc, rpr=1)

        uRng = mc.getAttr(inSurface + '.minMaxRangeU')
        vRng = mc.getAttr(inSurface + '.minMaxRangeV')

        # Create duplicate inSurface
        surface = mc.duplicate(inSurface, n='tmp_surface_1')[0]
        for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
            mc.setAttr(surface + '.' + attr, l=0)
        
        mc.makeIdentity(surface, t=1, r=1, s=1, apply=1)

        #Create node closestPointOnSurface
        pointSurf = mc.createNode('closestPointOnSurface', n='tmp_closestPointOnSurface_1' )
        mc.connectAttr(surface + '.local', pointSurf + '.inputSurface')
        mc.connectAttr(loc + '.translate', pointSurf + '.inPosition')

        #Get uv coords
        u = mc.getAttr(pointSurf + '.u')
        v = mc.getAttr(pointSurf + '.v')

        #Normalized uv's then set follicle paramenters
        normU = abs( u / uRng[0][1] )
        normV = abs( v / vRng[0][1] )

        mc.setAttr(fols + '.parameterU', normU)
        mc.setAttr(fols + '.parameterV', normV)

        mc.delete(pointSurf, loc, surface)

    return folList


##########################################################
''' Copy Skin To Nurbs - 01/06/2017 '''
##########################################################

def copy_skin_to_nurbs(inSkinnedObj, inSurface):
    """
    copy_skin_to_nurbs  - 01/06/2017.
    Args:
        inSkinnedObj: Skinned mesh PyNode object
        inSurface: Nurbs PyNode object
    Returns:
        PyNode : targetSkinCluster
    Raises:
        None.
    Usage :
        copy_skin_to_nurbs(inSkinnedObj, inSurface)
    """

    poly = pm.PyNode(pm.nurbsToPoly(inSurface, format=3, ch=0)[0])
    bindJs = [pm.PyNode(obj) for obj in getBindJoints(inSkinnedObj.name())]
    
    #--- Add skinCluster if it doesn't exist
    try:
        targetSkinCluster = inSurface.listHistory(type='skinCluster')[0]
        #--- Make sure all bindJs are in the targetSkinCluster
        skinnedJs = targetSkinCluster.getInfluence()
        for j in bindJs:
            if not j in skinnedJs:
                targetSkinCluster.addInfluence(j)
                pm.warning(j + ' joint added to skinCluster')
    except:
        targetSkinCluster = pm.skinCluster( bindJs, inSurface, dr=4.5, removeUnusedInfluence=0, maximumInfluences=1, frontOfChain=0, toSelectedBones=1, n = inSurface + '_skC')

    #--- Get skinCluster from inSkinnedObj
    skinClusterOri = inSkinnedObj.listHistory(type='skinCluster')[0]

    #poly newSkinClusterDef
    polySkinCluster = pm.skinCluster( bindJs, poly, dr=4.5, removeUnusedInfluence=0, maximumInfluences=1, frontOfChain=0, toSelectedBones=1, n = poly + '_2_skC')
    pm.copySkinWeights( ss=skinClusterOri, ds=polySkinCluster, noMirror=True, surfaceAssociation='closestPoint', influenceAssociation='oneToOne' )

    # Copy skin to inSurface components
    pm.select(poly, inSurface.cv, r=1)
    pm.copySkinWeights( noMirror=True, surfaceAssociation='closestPoint', influenceAssociation='oneToOne' )

    pm.delete(poly)

    return targetSkinCluster


###########################################################################
''' Copy Weights Nurbs - (Julien Version - depricated) 27/02/2017 ''' ###
###########################################################################
def copy_weights_nurbs() :

    #####switches  True/False   ####
    ClosedShape = 'False'

    ### gettingTargets from Selection , first source then nurbs ###
    inTargets = mc.ls( sl = True )

    inSkinSource = inTargets[0]
    inNurbsTarget = inTargets[1]
    inNurbsShape = mc.listRelatives ( inNurbsTarget , shapes = True )


    ### getting variables for loops from nurbsSurface ###
    inUspans = mc.getAttr( '%s.spansU' % inNurbsShape[0] )
    inVspans = mc.getAttr( '%s.spansV' % inNurbsShape[0] )
    inUDeg = mc.getAttr( '%s.degreeU' % inNurbsShape[0] )
    inVDeg = mc.getAttr( '%s.degreeV' % inNurbsShape[0] )
    inUForm = mc.getAttr( '%s.formU' % inNurbsShape[0] )
    inVForm = mc.getAttr( '%s.formV' % inNurbsShape[0] )

    if ( inUForm == 0 ) :
        inNurbsUCount = inUspans + inUDeg
    else :
        inNurbsUCount = inUspans

    if ( inVForm == 0 ) :
        inNurbsVCount = inVspans + inVDeg
    else :
        inNurbsVCount = inVspans
        
    #######################################################

    ###create poly convert of nurbs surface###
    inPolySource = ( '%s_polyConvert' % inNurbsTarget )
    mc.nurbsToPoly ( inNurbsTarget , f = 3 , pt = 1 , mnd = True,  n = inPolySource )


    mc.select(inSkinSource , inPolySource )


    ######
    ''' copy first mesh skinCluster to all others meshes '''
    sel = mc.ls(selection=True)

    if sel >= 2:
        skinClusterDef = mc.ls(mc.listHistory(sel[0], pdo=True),type='skinCluster')
        sizeVtx = mc.polyEvaluate(sel[0], vertex=True)
        vtx = '%s.vtx[0:%d]' % (sel[0], sizeVtx)
        skinJts = mc.skinPercent(skinClusterDef[0], vtx, transform=None, query=True)

        for each in sel[1:]:
            newSkinClusterDef = mc.skinCluster(skinJts, each, n='%s_skC' % each)[0]
            mc.copySkinWeights( ss=skinClusterDef[0], ds=newSkinClusterDef, noMirror=True )
            
        mc.skinCluster(skinJts, inNurbsTarget, n='%s_skC' % inNurbsTarget)
    ######


    skinClstrNurbs = mc.ls( mc.listHistory(inNurbsTarget) ,type='skinCluster')

    Uc = inNurbsUCount
    Vc = inNurbsVCount 

    mc.setAttr ( '%s.normalizeWeights' % skinClstrNurbs[0] , 0 )

    for i in range( 0 , Uc ) :
        for j in range ( 0 , Vc ) :
            
            vtxCount = (j + (inNurbsVCount * i))
            
            mc.select ('%s.vtx[%d]' % ( inPolySource ,vtxCount))        
            mel.eval("artAttrSkinWeightCopy;")
            
            mc.select ( '%s.cv[%d][%d]' % (inNurbsTarget , i , j ) )
            mel.eval("artAttrSkinWeightPaste;")
     
            ###progress###
            progPercent = ( ((vtxCount + 1.0 ) / ( inNurbsUCount * inNurbsVCount) ) * 100.0 )
            mc.headsUpMessage( 'CopySkin progression %d%% ' % progPercent  )
          
    mc.setAttr ( '%s.normalizeWeights' % skinClstrNurbs[0] , 1 )

    mc.delete (inPolySource)


###########################################################################
''' Convert trasform names to pascal case 06/02/2017 ''' ###################
###########################################################################
def to_pascal_case(inList):
    x = 0
    for each in inList:#pass
        if isinstance(each, pm.nodetypes.Transform):
            snake_str = each
            components = snake_str.split('_')

            newName = ''
            for com in components:#pass
                if com:
                    newString = com[0].upper()
                    for i, c in enumerate(com):#pass
                        if i == 0:
                            pass
                        else:
                            newString += c#.lower()
                    newName += newString
                    if not com == components[-1]:
                        newName += '_'

            if not each.name() == newName:
                oldName = each.name()
                pm.rename(each, newName)
                x = x+1
                print '%s ---> Object "%s" was renamed to "%s"' % (x, oldName, newName)
            else:
                pass

#to_pascal_case(pm.ls(sl=1))
#######################################################################################################
''' to_camel_case 06/02/2017 ''' ##################################################################
#######################################################################################################
def to_camel_case(snake_str):
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return components[0] + "".join(x.title() for x in components[1:])


#######################################################################################################
''' Rename Shapes ''' ############################################################################
#######################################################################################################
def rename_shapes(inTransform):
    shapes = mc.listRelatives(inTransform, shapes=1)
    if shapes:
        for each in shapes:
            mc.rename(each, '%sShape_1'%inTransform)

#######################################################################################################
''' Text at Origin 06/02/2017 ''' ##################################################################
#######################################################################################################
def text_at_origin(name='name', text = 'Write your text!', font='Utopia', size=28):

    fontData = "%s|wt:%s|sz:%s" % (font, 50, size)

    textGrp = mc.textCurves(ch=0, font=fontData, t=text)[0]

    #   get joint hierachy
    mc.select(textGrp, hi=True)
    crvList = mc.ls( sl=True, type = 'nurbsCurve' )

    configNode = create_grp(name)

    #   Create CP
    for s in crvList:
        parent = mc.listRelatives(s, parent=True)[0]
        #mc.makeIdentity(parent, )
        mc.parent(parent, configNode)
        mc.makeIdentity ( parent , apply = 1 )
        mc.parent(parent, w=1)
        mc.parent(s, configNode, r=1, s=1)
        mc.delete(parent)


    mc.CenterPivot(mc.select(configNode, r=1))
    mc.move(0, 0, 0, configNode, rpr=1)

    mc.makeIdentity ( configNode , apply = 1 )

    mc.delete(textGrp)
    
    rename_shapes(configNode)

    return configNode


#######################################################################################################
''' Connect Visibility 10/05/2016 ''' ##################################################################
#######################################################################################################
def connect_viz(inObjList, inVizAttr, inVizControl):
    """
    Connect Visibility  - 10/05/2016.
    Args:
        inObjList: This is the list of objects to be driven by the inVizAttr
        inVizAttr: Name of the on/off attribute.
        inVizControl: Node that will receive driver attribute.
    Returns:
        None.
    Raises:
        None.
    """
    if not mc.attributeQuery(inVizAttr, node=inVizControl, exists=True):
        mc.addAttr( inVizControl, ln=inVizAttr, at='enum', en='off:on:' )
        mc.setAttr( inVizControl + '.' + inVizAttr, e=1, keyable=1 )

    # Connect vizibility
    if inObjList:
        for s in inObjList:
            try:
                mc.connectAttr( inVizControl + '.' + inVizAttr, s + '.v', f=True)
            except:
                mc.warning('Skipping...')


#######################################################################################################
''' Add Tag Attribute 02/05/2016 ''' ##################################################################
#######################################################################################################
# Add tag attribute '''
def add_tag_attr(inObj, attributeName = None, attributeType = "float"):

    if not attributeName:
        attributeName = 'tmp_attr'

    #Force inObj to be a list
    inNodeList = force_return_list(inObj)

    for node in inNodeList:
        #Add tag attr
        if not (mc.attributeQuery( attributeName, node=node, ex=True )):
            mc.addAttr(node, longName = attributeName, attributeType = attributeType)

#  Add tag attribute '''
def get_nodes_with_attribute(inAttributeName):
    attrList = mc.ls('*.%s'%inAttributeName, r=True)

    #Remove attrs from node names
    nodeList = []

    if attrList:
        for each in attrList:
            nodeList.append(each.split('.')[0])

    return nodeList


#######################################################################################################
''' Data to node attribute 22/04/2016 ''' #############################################################
#######################################################################################################
def data_to_node_attr(inData, inNode, inAttributeName):
    '''
    Get data info from attr:
    attrValue = eval(mc.getAttr('%s.%s' % (inNode, inAttributeName)))
    '''
    vAttributeType = "string"

    # --- Convert to str
    stringValue = str(inData)

    # --- Create Attribute with datat info
    if not (mc.attributeQuery( inAttributeName, node=inNode, ex=True )):
            mc.addAttr(inNode, longName = inAttributeName, dataType = vAttributeType )
    mc.setAttr('%s.%s' % (inNode, inAttributeName), stringValue, type="string", lock=True)


def data_from_node_attr(inNode, inAttributeName):
    '''
    Get data info from attr:
    '''
    data = ''
    if mc.objExists( inNode ):
        if mc.attributeQuery( inAttributeName, node=inNode, ex=True):
            data = eval(mc.getAttr('%s.%s' % (inNode, inAttributeName)))
    if data:
        return data
    else:
        return


#######################################################################################################
''' Create group 21/04/2016 ''' #######################################################################
#######################################################################################################
def create_grp(name):

    if not mc.objExists( name ):
        name = mc.createNode('transform', n=name)

    return name


#######################################################################################################
''' setRGBColor Win ''' ############################################################################
#######################################################################################################
def setRGBColor():
    mc.colorEditor()
    if mc.colorEditor(query=True, result=True):
        rgb = mc.colorEditor(query=True, rgb=True)
        print 'RGB = ' + str(rgb)
    else:
        print 'Editor was dismissed'

    sl = mc.ls(sl=1)
    for s in sl:
        mc.setAttr(s + '.overrideEnabled', True)
        if rgb:
            mc.setAttr(s + '.overrideRGBColors', 1)
            mc.setAttr(s + ".overrideColorR", rgb[0])
            mc.setAttr(s + ".overrideColorG", rgb[1])
            mc.setAttr(s + ".overrideColorB", rgb[2])
        else:
            mc.setAttr(s + '.overrideRGBColors', 0)
            mc.setAttr(s + '.overrideColor', colorOverride)


#######################################################################################################
''' Color Shapes 20/04/2016 ''' #######################################################################
#######################################################################################################
def color_shapes(obj, rgb=None, colorOverride=17):

    shapes = mc.listRelatives(obj, s=1)

    for s in shapes:
        mc.setAttr(s + '.overrideEnabled', True)
        if rgb:
            mc.setAttr(s + '.overrideRGBColors', 1)
            mc.setAttr(s + ".overrideColorR", rgb[0])
            mc.setAttr(s + ".overrideColorG", rgb[1])
            mc.setAttr(s + ".overrideColorB", rgb[2])
        else:
            mc.setAttr(s + '.overrideRGBColors', 0)
            mc.setAttr(s + '.overrideColor', colorOverride)


#######################################################################################################
''' Blend color override RGB values 31/03/2016 ''' ##########################################################
#######################################################################################################
def blend_color_override_rgb_values(inManipList, originValueList, targetValueList):

    factorList = []
    for oriV, trgV in zip(originValueList, targetValueList) :
        addFactor = (oriV - trgV)/len(inManipList)
        factorList.append(abs(addFactor))

    stepR = originValueList[0]
    stepG = originValueList[1]
    stepB = originValueList[2]

    for i, s in enumerate(inManipList):#pass

        #Get shape node
        shape = mc.listRelatives(s, s=1)[0]
        # Enable overrides
        mc.setAttr(shape + ".overrideEnabled", 1)
        mc.setAttr(shape + ".overrideRGBColors", 1)

        if i == 0:
            stepR += factorList[0]
            stepG += factorList[1]
            stepB += factorList[2]
            mc.setAttr(shape + ".overrideColorR", originValueList[0])
            mc.setAttr(shape + ".overrideColorG", originValueList[1])
            mc.setAttr(shape + ".overrideColorB", originValueList[2])
        elif i == len(inManipList)-1:
            mc.setAttr(shape + ".overrideColorR", targetValueList[0])
            mc.setAttr(shape + ".overrideColorG", targetValueList[1])
            mc.setAttr(shape + ".overrideColorB", targetValueList[2])
        else:

            signR = 1
            signG = 1
            signB = 1

            if originValueList[0] > targetValueList[0]:
                signR = -1
            if originValueList[1] > targetValueList[1]:
                signG = -1
            if originValueList[2] > targetValueList[2]:
                signB = -1

            stepR += factorList[0] * signR
            stepG += factorList[1] * signG
            stepB += factorList[2] * signB

            mc.setAttr(shape + ".overrideColorR", stepR)
            mc.setAttr(shape + ".overrideColorG", stepG)
            mc.setAttr(shape + ".overrideColorB", stepB)


#######################################################################################################
''' Order List Hierarchically 19/02/2016 ''' ##########################################################
#######################################################################################################

def order_list_hierarchically(inChildrenList):
    '''
    From a list of parents and a list of children, reorder the inChildrenList hierarchically,
    Todo: - Error checking
    '''

    inTopNodeList = get_all_top_parents(inChildrenList)

    orderedManipExtendedList = []
    for s in inTopNodeList:

        #Check all parents
        allDescendents = mc.listRelatives(s, allDescendents=1)

        branchEndList = []
        if allDescendents:
            for d in allDescendents:
                childrenList = mc.listRelatives(d, c=1)

                if not childrenList:
                    branchEndList.append(d)

        parentsList = []
        for be in branchEndList:
            parents = mc.ls(be, long=True)[0].split('|')#[1:-1]
            parents_long_named = ['|'.join(parents[:i]) for i in xrange(1, 1 + len(parents))]
            #parentsList.append(parents_long_named)
            parentsList.append(parents)

        #Get new list in the right order
        newList = []
        for i, eachList in enumerate(parentsList):
            for x, each in enumerate(eachList):
                if each not in newList:
                    newList.append(each)

        #Get ordered manip list
        orderedManipList = []
        for each in newList:
            if each in inChildrenList:
                orderedManipList.append(each)

        orderedManipExtendedList.extend(orderedManipList)

    return orderedManipExtendedList


def get_all_top_parents(inList):
    topList = []
    lsCp = [ topList.append(mc.ls(s, long=True)[0].split('|')[1]) for s in inList if not topList.count(mc.ls(s, long=True)[0].split('|')[1]) > 0 ]

    return topList


#######################################################################################################
''' trans_rivet : Rivet with translation values only 29/03/2016 ''' ###################################
#######################################################################################################

def trans_rivet(inVtx, name=None):

    import re

    objA = inVtx.split('.')[0]
    #objB = edgeB.split('.')[0]
    nodes = []

    if not name :
        name = 'trs_rivet'

    ###---  build system
    #get edge
    mc.select(inVtx, r=1)
    mc.ConvertSelectionToEdges()
    edge = mc.ls(sl=1, fl=1)[0]

    #---  curves
    cfme = mc.createNode('curveFromMeshEdge', n='%s_%s_cfme' %(name, objA))
    mc.setAttr('%s.ei[0]' %cfme, int(re.findall('\d+', edge)[-1]))
    mc.connectAttr('%s.w' %objA, '%s.im' %cfme, f=True)

    poci = mc.createNode('pointOnCurveInfo', n='%s_%s_poci' %(name, objA))
    mc.connectAttr('%s.outputCurve' %cfme, '%s.inputCurve' %poci, f=True)

    loc = mc.spaceLocator(n='%s_loc'%name)[0]

    mc.connectAttr('%s.result.position' %poci, '%s.translate' %loc, f=True)
    mc.setAttr('%s.turnOnPercentage' %poci, 1)

    tmpLoc = mc.spaceLocator(n='tmp_rivet_loc')[0]
    snapToTarget(tmpLoc, inVtx)

    dist = getDistanceBetween(tmpLoc, loc)

    tol = .0000001
    if dist > tol:
        print dist
        mc.setAttr('%s.parameter' %poci, 1)

    mc.delete(tmpLoc)

    return loc


def create_trans_rivet_on_vertex_list(vertexList, name=None):

    if not name :
        name = 'trs_rivet'

    #Create parent group
    parentGrp = createParentGrp('%s_grp'%name)
    locList = []
    for i, each in enumerate(vertexList):

        loc = trans_rivet(each, name='%s_%s'%(name, i))
        locList.append(loc)
        mc.parent(loc, parentGrp)

    return locList, parentGrp


#Create group
def createParentGrp(name):

    if not mc.objExists( name ):
        grp = mc.createNode('transform', n=name)

    return grp


#######################################################################################################
''' Set Soft Selection To Joint 2015 ''' ##############################################################
#######################################################################################################

def getSoftSelection (opacityMult=1.0):
	allDags, allComps, allOpacities = [], [], []

	# if soft select isn't on, return
	if not mc.softSelect(q=True, sse=True):
		return allDags, allComps, allOpacities
		
	richSel = om.MRichSelection()
	try:
		# get currently active soft selection
		om.MGlobal.getRichSelection(richSel)
	except:
		raise Exception('Error getting soft selection.')

	richSelList = om.MSelectionList()
	richSel.getSelection(richSelList)
	selCount = richSelList.length()

	for x in xrange(selCount):
		shapeDag = om.MDagPath()
		shapeComp = om.MObject()
		try:
			richSelList.getDagPath(x, shapeDag, shapeComp)
		except RuntimeError:
			# nodes like multiplyDivides will error
			continue
		
		compOpacities = {}
		compFn = om.MFnSingleIndexedComponent(shapeComp)
		try:
			# get the secret hidden opacity value for each component (vert, cv, etc)
			for i in xrange(compFn.elementCount()):
				weight = compFn.weight(i)
				compOpacities[compFn.element(i)] = weight.influence() * opacityMult
		except Exception, e:
			print e.__str__()
			print 'Soft selection appears invalid, skipping for shape "%s".' % shapeDag.partialPathName()

		allDags.append(shapeDag)
		allComps.append(shapeComp)
		allOpacities.append(compOpacities)
		
	return allDags, allComps, allOpacities

#allDags, allComps, allOpacities = getSoftSelection()

def setSoftSelectionToJoint(inJoint):
    mesh = mc.ls(sl=1)[0].split('.')[0]

    weights = getSoftSelection()[2][0]
    skC = mc.ls(mc.listHistory(mesh),type='skinCluster')[0]
    vtxNum = weights.keys()

    for n in vtxNum:
        vertex = '%s.vtx[%s]'%(mesh, n)
        value = weights[n]
        mc.skinPercent(skC, vertex, transformValue=[(inJoint, value)])

#inJoint = mc.ls(sl=1)[0]
#setSoftSelectionToJoint(inJoint)
#######################################################################################################
''' create Measure On Selected 17/12/2015 ''' #########################################################
#######################################################################################################

def createMeasureTool(startObj, endObj):
    '''- createMeasureOnSelected help
    
    Description:  Temporary mel version from Jason Schleifer. Creates a measure tool at the location of the given items
    Dependencies: NONE
    Date:         21/09/2015
    Example:      start, end = mc.ls(os=1)
                  res = createMeasureOnSelected(start, end)
    
    '''
    mel.eval('''
    /*
        Script:     js_createMeasureTool
        Version:    1.0
        Author:     Jason Schleifer
        Website:    http://jonhandhisdog.com
        Descr:      Creates a measure tool at the location of the given items
    */
    global proc string[] js_createMeasureTool (string $startJoint, string $endJoint)
    {
        string $return[0];
        float $startPos[0];
        float $endPos[0];
        $startPos = `xform -q -ws -rp $startJoint`;
        $endPos = `xform -q -ws -rp $endJoint`;
        // create the locators by hand4
        $tmpLoc = `spaceLocator -name ($startJoint + "_distance_start")`;
        $tmpLoc2 = `spaceLocator -name ($startJoint + "_distance_end")`;
        move -a -ws $startPos[0] $startPos[1] $startPos[2] $tmpLoc[0];
        move -a -ws $endPos[0] $endPos[1] $endPos[2] $tmpLoc2[0];
       
        $dimension = `createNode distanceDimShape `;
        connectAttr ($tmpLoc[0] + ".worldPosition[0]") ($dimension + ".startPoint");
        connectAttr ($tmpLoc2[0] + ".worldPosition[0]") ($dimension + ".endPoint");
        //$dimension = `distanceDimension -sp $startPos[0] $startPos[1] $startPos[2] -ep $endPos[0] $endPos[1] $endPos[2]`;
       
        //select $dimension;
        //$sp = `js_getAttachedObjects "startPoint"`;
        //$ep = `js_getAttachedObjects "endPoint"`;
        //$sp[0] = `rename $sp[0] ($startJoint + "_distance_start")`;
        //$ep[0] = `rename $ep[0] ($startJoint + "_distance_end")`;
        $parent = `listRelatives -f -p $dimension`;
        $newName = `rename $parent[0] ($startJoint + "_distance")`;
        
        $return[0] = $newName;
        $return[1] = $tmpLoc[0];
        $return[2] = $tmpLoc2[0];
        return $return;
    }
    ''')

    res = mel.eval('js_createMeasureTool("%s", "%s")'%(startObj, endObj))
    
    return res


#######################################################################################################
''' xyShrinkWrap 03/04/2017 ''' #########################################################
#######################################################################################################

def xyShrinkWrap():
    '''- createMeasureOnSelected help
    
    Description:  Temporary mel version from xyShrinkWrap
    Dependencies: NONE
    Date:         03/04/2017
    Example:      startObj, targetObj = mc.ls(sl=1)
                  res = xyShrinkWrap(startObj, targetObj)
    
    '''
    #mc.select(startObj, targetObj, r=1)
    sl = mc.ls(sl=1)
    mel.eval('''
    proc warn( string $mod, string $msg )
    {
        warning("xyShrinkWrap::"+$mod+"(): "+$msg);
    }


    global proc string toshape( string $n )
    {
        string	$s[];

        if (objExists($n))
        {
            $s=`listRelatives -pa -s -ni $n`;
            $s=`ls -type controlPoint $n $s[0]`;
        }
        
        return($s[0]);
    }


    proc wrapc( string $c, string $n ) // component (node.attr), wrapper transform
    {
        float	$p[];
        
        $p=`xform -q -ws -t $c`; xform -ws -t $p[0] $p[1] $p[2] $n;
        $p=`xform -q -ws -t $n`; xform -ws -t $p[0] $p[1] $p[2] $c;
    }


    proc wrap( string $ss[], string $ds ) // source transform(s)/shape(s)/component(s), destination geometry shape 
    {
        global string	$gMainProgressBar;
        string		$s, $n, $sh;
        int		$p;
        
        print($ss);
        
        if (size(`ls -type controlPoint $ds`))
        {
            $n=`group -w -em -n "n1"`;							// create temp ('snapper') null
            geometryConstraint $ds $n;

            progressBar -e -bp -ii 1 -min 0 -max (size($ss)) -st "Shrinkwrapping..." $gMainProgressBar;

            for($s in $ss)
            {
                if (`progressBar -q -ic $gMainProgressBar`) break;
                
                if (match("[^.]+[.][^.]+[\[].+[\]]",$s)=="")				// (check for component format)
                {
                    // object
                    
                    $sh=$s;
                    
                    if (size(`ls -tr $s`))						// transform node
                    {
                        if (($sh=toshape($s))=="")				// find shape node
                        {
                            wrapc($s,$n);					// no shape: snap transform
                            $sh="";
                        }
                    }
                    
                    if (($sh!="")&&size(`ls -type controlPoint $sh`))		// geom. shape node: snap all control points
                    {
                        $m=`getAttr -s ($sh+".controlPoints")`;
                        $p=`progressBar -q -pr $gMainProgressBar`;
                        
                        progressBar -e -min 0 -max $m -st "Wrapping object..." $gMainProgressBar;
                        
                        for($i=0;$i<$m;$i++)
                        {
                            if (`progressBar -q -ic $gMainProgressBar`) break;
                            progressBar -e -s 1 $gMainProgressBar;

                            wrapc($sh+".controlPoints["+$i+"]",$n);
                        }
                        
                        progressBar -e -min 0 -max (size($ss)) -pr $p -st "Wrapping components..." $gMainProgressBar;
                    }
                }
                else
                {
                    // component
                    
                    if (($s!="")&&objExists($s)) wrapc($s,$n);
                }
            }
            
            progressBar -e -ep $gMainProgressBar;
            delete($n);									// delete temp snapper null
        }
        else warn("wrap",$ds+" doesn't exist or not a surface shape");
    }


    global proc xyShrinkWrap()
    {
        string	$sl[]=`ls -fl -sl`, $d;
        int	$i, $m=size($sl);
        
        if ( ($m>1)&&(($d=toshape($sl[$m-1]))!="") )
        {
            $sl[$m-1]="";
            wrap($sl,$d);
        }
        else warn("xyShrinkWrap","Select some objects; select object to shrinkwrap to last");
    }
    
    ''')
    
    mel.eval('xyShrinkWrap()')
    mc.select(sl, r=1)


#######################################################################################################
''' getBindJoints 16/12/2015 '''##############################################################
#######################################################################################################
#Todo: Accept other objects besides meshes
def getBindJoints(inObject):
    
    skinCluster = mc.ls(mc.listHistory(inObject),type='skinCluster')
    sizeVtx = mc.polyEvaluate(inObject , vertex=True)
    vtx = '%s.vtx[0:%d]' % (inObject, sizeVtx)  
    skinJts = mc.skinPercent(skinCluster[0], vtx, transform=None, query=True)

    return skinJts


#######################################################################################################
''' mirror selected shapes 25/11/2015 ''' ################################################################
#######################################################################################################
#Select controls curves (ex. 'leg_front_l_ik_ctrl'), and set the replace tag ('_l_', '_r_')
def mirrorControlShapes(right = '_r_', left = '_l_'):


    sl = mc.ls(sl=1)

    for s in sl:
        dup = mc.duplicate(s, rc=1)[0]
        shapes = mc.listRelatives(dup, shapes=1)
        tmp = mc.createNode('transform')

        mc.parent(tmp, dup)

        mc.xform(tmp, t=(0, 0, 0), ro=(0, 0, 0), scale=(1, 1, 1))

        mc.parent(tmp, w=1)

        for sh in shapes:
            mc.parent(sh, tmp, r=1, s=1)
            
        mc.delete(dup)

        neg = mc.createNode('transform')
        mc.parent(tmp, neg)

        mc.setAttr('%s.sx'%neg, -1)

        target = s.replace(left, right)

        if mc.objExists(target):
            mc.parent(tmp, target)
            mc.makeIdentity(tmp, apply=True, t=True, r=True, s=True)

            mc.parent(tmp, w=1)

            shapesDel = mc.listRelatives(target, shapes=1)
            if shapesDel:
                mc.delete(shapesDel)

            shapes = mc.listRelatives(tmp, shapes=1)

            for sh in shapes:
                mc.parent(sh, target, r=1, s=1)
                
        else:
            mc.warning('%s not found!'%target)

        mc.delete(tmp, neg)


#######################################################################################################
''' mirrorNegativeScaleX 25/11/2015 '''##############################################################
#######################################################################################################

def mirrorNegativeScaleX():
    
    objList = []

    sl = mc.ls(os=1)
    for o in sl:
        #pass
        if '_l_' in o:
            dupMirrorList = mc.duplicate(o, n=o.replace('_l_', '_r_'))
        elif '_r_' in o:
            dupMirrorList = mc.duplicate(o, n=o.replace('_r_', '_l_'))
        else:
            dupMirrorList = mc.duplicate(o, n=o)

        for obj in dupMirrorList:
            mc.setAttr(obj + ".tx", lock= False, keyable=True)
            mc.setAttr(obj + ".ty", lock= False, keyable=True)
            mc.setAttr(obj + ".tz", lock= False, keyable=True)
            mc.setAttr(obj + ".rx", lock= False, keyable=True)
            mc.setAttr(obj + ".ry", lock= False, keyable=True)
            mc.setAttr(obj + ".rz", lock= False, keyable=True)
            mc.setAttr(obj + ".sx", lock= False, keyable=True)
            mc.setAttr(obj + ".sy", lock= False, keyable=True)
            mc.setAttr(obj + ".sz", lock= False, keyable=True)
            mc.setAttr(obj + ".v", lock= False, keyable=True)

            #firstParent = mc.listRelatives(o, p=1)
            mc.select(cl=1)
            dupGrp = mc.group(em=1)

            mc.parent(obj, dupGrp)

            mc.setAttr(dupGrp + ".scaleX", -1)
            mc.ungroup(dupGrp)

            #mc.parent(obj, w=1)

            objList.append(obj)

    mc.select(objList)



#Mel version
'''
global proc fs_mirrorX ()
{
string $dupMirror[] = `duplicate`;
string $obj;
		for ($obj in $dupMirror)
		{
			setAttr -lock false -keyable true ($obj + ".tx");
			setAttr -lock false -keyable true ($obj + ".ty");
			setAttr -lock false -keyable true ($obj + ".tz");
			setAttr -lock false -keyable true ($obj + ".rx");
			setAttr -lock false -keyable true ($obj + ".ry");
			setAttr -lock false -keyable true ($obj + ".rz");
			setAttr -lock false -keyable true ($obj + ".sx");
			setAttr -lock false -keyable true ($obj + ".sy");
			setAttr -lock false -keyable true ($obj + ".sz");
			setAttr -lock false -keyable true ($obj + ".v");
		}
string $dupGrp = `group`;
string $firstParent = firstParentOf($dupGrp);
if ($firstParent != "")
{
parent -w;
}
ungroup $dupGrp;
string $dupGrp_II = `group`;
xform -os -piv 0 0 0;
setAttr ($dupGrp_II + ".scaleX") -1;
ungroup $dupGrp_II;
}
fs_mirrorX;
'''

#######################################################################################################
''' createObjsOnSelected 20/11/2015 '''##############################################################
#######################################################################################################

def createObjsOnSelected(objList, type='curve', degree=1 ):
    ''' 
    rlx.createObjsOnSelected(objList, type='curve', degree=1) 
    Possible types : 'curve', 'joint', 'jointChain', 'locator'
    '''

    posList = getPosListFromObjects(objList)
    
    resObjList = []

    if type == 'jointChain':
        returnObj = chainFromPositionList(posList)

    elif type == 'curve':

        if degree == 1 or degree == 2 or degree == 3 or degree == 5 or degree == 7:
            curve = mc.curve(p=(posList), degree=degree)
            returnObj = curve
        else:
            mc.error('Degree value must be 1, 2, 3, 5 or 7!')


    elif type == 'locator':
        
        grp = mc.createNode('transform', n='objs_locators_grp')

        for i, p in enumerate(posList):
            startLoc = mc.spaceLocator(n='%s_%s_loc'%(objList[i], i))[0]
            mc.move(p[0], p[1], p[2], startLoc, rotatePivotRelative=True, worldSpace=True)
            mc.parent(startLoc, grp)
            resObjList.append(startLoc)
        
        returnObj = resObjList


    elif type == 'joint':
        
        grp = mc.createNode('transform', n='joints_grp')

        for p in posList:
            mc.select(cl=1)
            sJnt = mc.joint(p=(p))
            mc.parent(sJnt, grp)
            resObjList.append(sJnt)

        returnObj = resObjList

    else:
        mc.error('type flag must be joint, jointChain, curve, or locator!')
    
    if returnObj:
        return posList, returnObj


#######################################################################################################
''' resetSkinCluster  '''##########################################################################
#######################################################################################################

def resetSkinCluster():
    sel = mc.ls(selection=True)

    for each in sel:
        skinClusterDef = mc.ls(mc.listHistory(each, pdo=True),type='skinCluster')

        if skinClusterDef:
            infs = mc.listConnections( skinClusterDef[0] + '.matrix' )

            for i, inf in enumerate( infs ):

                m = mc.getAttr( inf + '.worldInverseMatrix' )
                mc.setAttr( skinClusterDef[0] + '.bindPreMatrix[' + str(i) + ']', m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10], m[11], m[12], m[13], m[14], m[15], typ= 'matrix' )


#######################################################################################################
''' Counter Transformations  2013 ''' #################################################################
#######################################################################################################
def counterTransformations(inList):
    '''- counterTransformations help
    
    Description:  Lock position of a transform by counter animating parent groups with multiplyDivide nodes.
    Dependencies: NONE
    Date:         21/09/2015
    Example:      res = counterTransformations(mc.ls(sl=1))
    
    '''
    rotOrderTuple = ('xyz', 'yzx', 'zxy', 'xzy', 'yxz', 'zyx')

    for s in inList:
        rotOrder = rotOrderTuple[mc.getAttr('%s.rotateOrder' % s)]

        #Get counter rotation order
        rotOrderList = list(rotOrder)
        countRotOrder = rotOrderList[2] + rotOrderList[1] + rotOrderList[0]


        offset = mc.duplicate(s, po=1, n='%s_offset' %s)[0]
        trans = mc.duplicate(s, po=1, n='%s_counter_%s' % (s, countRotOrder.upper()))[0]

        mc.parent(trans, offset)
        mc.parent(s, trans)

        #Create md to negate the value
        mdRot = mc.createNode('multiplyDivide', n='%s_rot_md'%s)

        mc.connectAttr('%s.rotate' % s, '%s.input1' % mdRot)
        mc.setAttr('%s.input2X' % mdRot, -1)
        mc.setAttr('%s.input2Y' % mdRot, -1)
        mc.setAttr('%s.input2Z' % mdRot, -1)

        #connect to rot groups
        mc.connectAttr('%s.output%s' % (mdRot, rotOrder[0].upper()), '%s.r%s' % (trans, rotOrder[0]))
        mc.connectAttr('%s.output%s' % (mdRot, rotOrder[1].upper()), '%s.r%s' % (trans, rotOrder[1]))
        mc.connectAttr('%s.output%s' % (mdRot, rotOrder[2].upper()), '%s.r%s' % (trans, rotOrder[2]))


        #Translation
        mdTrs = mc.duplicate(mdRot, po=1, n='%s_trs_md'%s)[0]
        mc.connectAttr('%s.translate' % s, '%s.input1' % mdTrs)
        mc.connectAttr('%s.output' % mdTrs, '%s.translate' % trans)


        #Set reverse rotation order
        for i, each in enumerate(rotOrderTuple):
            if each == countRotOrder:
                mc.setAttr(trans + '.rotateOrder', i)

'''
DEPRECATED
def counterTransformations(inList):
    
    rotOrderTuple = ('xyz', 'yzx', 'zxy', 'xzy', 'yxz', 'zyx')
    
    rotPList = []

    for s in inList:
        rotOrder = rotOrderTuple[mc.getAttr('%s.rotateOrder' % s)]

        rotP = mc.duplicate(s, po=1, n='%s_counterT_grp' % s)[0]
        rotPList.append(rotP)
        
        rotA = mc.duplicate(s, po=1, n='%s_r%s' % (s, rotOrder[0]))[0]
        rotB = mc.duplicate(s, po=1, n='%s_r%s' % (s, rotOrder[1]))[0]
        rotC = mc.duplicate(s, po=1, n='%s_r%s' % (s, rotOrder[2]))[0]
        trans = mc.duplicate(s, po=1, n='%s_trs_%s%s%s' % (s, rotOrder[0].upper(), rotOrder[1].upper(), rotOrder[2].upper()))[0]

        mc.parent(rotC, rotB)
        mc.parent(rotB, rotA)
        mc.parent(trans, rotC)
        mc.parent(s, trans)
        mc.parent(rotA, rotP)

        #Create md to negate the value
        mdRot = mc.createNode('multiplyDivide', n='%s_rot_md'%s)

        mc.connectAttr('%s.rotate' % s, '%s.input1' % mdRot)
        mc.setAttr('%s.input2X' % mdRot, -1)
        mc.setAttr('%s.input2Y' % mdRot, -1)
        mc.setAttr('%s.input2Z' % mdRot, -1)

        #connect to rot groups
        mc.connectAttr('%s.output%s' % (mdRot, rotOrder[0].upper()), '%s.r%s' % (rotA, rotOrder[0]))
        mc.connectAttr('%s.output%s' % (mdRot, rotOrder[1].upper()), '%s.r%s' % (rotB, rotOrder[1]))
        mc.connectAttr('%s.output%s' % (mdRot, rotOrder[2].upper()), '%s.r%s' % (rotC, rotOrder[2]))

        #Translation
        mdTrs = mc.duplicate(mdRot, po=1, n='%s_trs_md'%s)[0]
        mc.connectAttr('%s.translate' % s, '%s.input1' % mdTrs)
        mc.connectAttr('%s.output' % mdTrs, '%s.translate' % trans)
    
    return rotPList
'''



#######################################################################################################
''' findPoleVctPlane  2013 '''#########################################################################
#######################################################################################################

def findPoleVctPlane(inPos1, inPos2, inPos3, name='tmp', keepLoc=True):
    '''- findPoleVctPlane help
    
    Description:  From a list of points positions it returns a list of tuples with world space position and rotation, 
                  defining the triangle plane. keepLoc should be on if the locators setup needs to be kept. 
    Dependencies: NONE
    Date:         31/08/2015
    Example:      t1, t2, t3 = mc.ls(sl=1)
                  pos1 = mc.xform(t1, q=1, ws=1, rp=1)
                  pos2 = mc.xform(t2, q=1, ws=1, rp=1)
                  pos3 = mc.xform(t3, q=1, ws=1, rp=1)
                  res = findPoleVctPlane(pos1, pos2, pos3, name='testing')
    '''
    #creat 3 locs
    locA = mc.spaceLocator(n='%s_locA'%name)[0]
    mc.xform(locA , ws =1 , t= inPos1)
    locB = mc.spaceLocator(n='%s_locB'%name)[0]
    mc.xform(locB , ws =1 , t= inPos2)
    locC = mc.spaceLocator(n='%s_locC'%name)[0]
    mc.xform(locC , ws =1 , t= inPos3)
    locR = mc.spaceLocator(n='%s_locResult'%name)[0]

    offset = mc.duplicate(locR, po=1, n='%s_offset'%locR)[0]
    mc.parent(locR, offset)

    mc.pointConstraint(locA, locC, offset)
    mc.aimConstraint(locB, offset, worldUpType="object", worldUpObject=locA)
    
    grp = mc.createNode('transform', n='%s_findPlane_grp'%name)
    mc.parent(locA, locB, locC, offset, grp)
    
    polePos = mc.xform(locR, q=1, ws=1, rp=1)
    poleRot = mc.xform(locR, q=1, ws=1, rotation=1)

    if keepLoc:
        return polePos, poleRot, locR, locA, locB, locC, grp
    else:
        mc.delete(grp)
        return polePos, poleRot

def createPoleVectorSetupLoc():
    sl = mc.ls(os=1, fl=1)
    posList = getPosListFromObjects(sl)
    poleVList = findPoleVctPlane(posList[0], posList[1], posList[2])
    mc.select(poleVList[2], r=1)
    
    return poleVList

#################################################################################################################################
''' selectClosestVerticesFromMesh 2013 '''
############################################################################################################################################
def selectClosestVerticesFromMesh():
    ori, sym = mc.ls(sl=1)

    oriVtx = mc.ls(ori + '.vtx[*]', fl=1)

    #create cpom
    cpom = mc.createNode('closestPointOnMesh', n='tmp_closestPointOnMesh')
    #get shape
    shape = mc.listRelatives(sym, s=1)[0]
    mc.connectAttr('%s.outMesh'%shape, '%s.inMesh'%cpom)

    vtxToselect = []

    for v in oriVtx:
        #v = oriVtx[2]
        pos = mc.pointPosition(v, world=1)

        mc.setAttr('%s.inPositionX'%cpom, pos[0])
        mc.setAttr('%s.inPositionY'%cpom, pos[1])
        mc.setAttr('%s.inPositionZ'%cpom, pos[2])

        idRes = mc.getAttr('%s.closestVertexIndex'%cpom)

        correctPos = vtxToselect.append('%s.vtx[%s]'%(sym, idRes))


    mc.delete(cpom)
    mc.select(vtxToselect, r=True)

#################################################################################################################################
''' reorder_list_by_selected 2013 '''
############################################################################################################################################
def reorder_list_by_selected(inList):
    for o in inList:
        grp = mc.group(o)
        mc.ungroup(grp)
        #mc.delete(grp)
    mc.select(inList)

#################################################################################################################################
''' Create spine fk controls 2013 '''
############################################################################################################################################
#position control maintaining the orientation in rx
#Create offsets for all the hierarchy

def fkSetup(inJointList, name='tmp'):
    #Select control curve

    ctrl = mc.ls(sl=1)[0]

    #Select joints in hierarchy order!
    joints = mc.ls(sl=1)

    driver = mc.duplicate(joints[0], po=1, n='%sDriver'%joints[0])[0]
    driverSup = mc.duplicate(joints[0], po=1, n='%sDriverSupport'%joints[0])[0]

    parent = mc.listRelatives(joints[0], parent=1)[0]

    size = len(joints)

    mc.parent(driver, ctrl)

    mc.orientConstraint(driver, driverSup)
    mc.pointConstraint(driver, driverSup)

    #rotate
    mdRot = mc.createNode('multiplyDivide', n='%s_rot_md'%ctrl)
    mc.connectAttr('%s.rotate'%driverSup, '%s.input1'%mdRot)

    mc.setAttr('%s.operation'%mdRot, 2)
    mc.setAttr('%s.input2X'%mdRot, size)
    mc.setAttr('%s.input2Y'%mdRot, size)
    mc.setAttr('%s.input2Z'%mdRot, size)

    #translate
    mdTrs = mc.createNode('multiplyDivide', n='%s_trs_md'%ctrl)
    mc.connectAttr('%s.translate'%driverSup, '%s.input1'%mdTrs)

    mc.setAttr('%s.operation'%mdTrs, 2)
    mc.setAttr('%s.input2X'%mdTrs, size)
    mc.setAttr('%s.input2Y'%mdTrs, size)
    mc.setAttr('%s.input2Z'%mdTrs, size)

    for j in joints:
        mc.connectAttr('%s.output'%mdRot, '%s.rotate'%j)
        mc.connectAttr('%s.output'%mdTrs, '%s.translate'%j)



#################################################################################################################################
''' Unparent and reparent functions - Used before skinning 2013 '''
############################################################################################################################################

def unparentHierarchy(inObject):
    '''
    Usage : 
    childParentList = rlx.unparentHierarchy(inObjects)
    rlx.reparentHierarchy(childParentList)
    '''
    #inObject = mc.ls(sl=1, long=True)[0]
    mc.select(inObject, hi=True)
    allObj = mc.ls(sl=1, type="joint")

    childParentList = []

    for each in allObj[1:]:
        
        parent = mc.listRelatives(each, p=True)[0]
        
        childParentList.append([each, parent])
    
    for each in allObj[1:]:
        
        mc.parent(each, w=True)
        mc.warning(each)
        
    mc.warning(childParentList)
    
    return childParentList


def reparentHierarchy(inChildParentList):

    for each in inChildParentList:
        
        mc.parent(each[0], each[1])
        
    return each



#######################################################################################################
''' createSmearSkinGen 2013 ''' #######################################################################
#######################################################################################################

def createSmearSkinGen(inJoints, inMesh, divisions = 2):
    '''
    Usage : createSmearSkinGen(inJoints, inMesh, divisions = 2) 
    '''

    #create geo fro smoothing
    smooth = mc.duplicate(inMesh, n=inMesh + '_smooth')[0]

    blnd = mc.blendShape(inMesh, smooth, n='output_blnd', weight=[0,1.0])[0]
    #targets = mc.listAttr(blnd + '.w', m=1)
    #mc.setAttr(blnd + '.' + targets[0], 1, lock=1)

    pSmooth = mc.polySmooth(smooth, keepBorder=False, divisions=divisions)[0]

    #create outmesh
    outMesh = mc.duplicate(smooth, n=smooth + 'OutMesh')[0]
    vtxGeo = mc.ls(inMesh + '.vtx[*]', fl=1)

    #skin geo
    #skin = 'skinCluster28'
    skin = mc.skinCluster( inJoints, inMesh, dr=4.5, maximumInfluences=1, frontOfChain=1, toSelectedBones=1, n = 'layer_A_skC')
    outSkin = mc.skinCluster( inJoints, outMesh, dr=4.5, maximumInfluences=1, frontOfChain=1, toSelectedBones=1, n = 'outMesh_skC')

    #Get all vertex from smoothed inMesh
    vtxSmoothed = mc.ls(smooth + '.vtx[*]', fl=1)
    vtxSmoothedOut = mc.ls(outMesh + '.vtx[*]', fl=1)

    allDisplacement = []
    for j in inJoints:

        pos = mc.xform(j, q=1, ws=1, rp=1)
        
        displacement = []
        for v in vtxSmoothed: 
            
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
    mc.warning('Done collecting weights. Starting to set values on outMesh!')

    for i, j in enumerate(inJoints):
        for x, dis in enumerate(allDisplacement[i]):
            mc.skinPercent(outSkin[0], outMesh + '.vtx[' + str(x) + ']', transformValue=[(j, dis)])
            
            #Lock influence weights
            mc.setAttr(j + '.liw', 1)
            
    mc.warning('Done calculating weights.')
    
    #mc.parent(
    
    return outMesh, smooth

''' transferMultipleSkins '''
def transferMultipleSkins(inMeshList, inSkinGeneratorMesh):
    
    #get skin joints
    skinClusterDef = mc.ls(mc.listHistory(inSkinGeneratorMesh),type='skinCluster')

    sizeVtx = mc.polyEvaluate(inSkinGeneratorMesh , vertex=True)
    vtx = '%s.vtx[0:%d]' % (inSkinGeneratorMesh, sizeVtx)  

    skinJts = mc.skinPercent(skinClusterDef[0], vtx, transform=None, query=True)
    mc.select(skinJts, r=1)

    #skin
    for i, g in enumerate(inMeshList):
        folSkin = mc.skinCluster( skinJts, g, dr=4.5, maximumInfluences=1, frontOfChain=0, toSelectedBones=1, n = g + '_skC')
        mc.select(inSkinGeneratorMesh, r=1)
        mc.select(g, add=1)
        mel.eval('copySkinWeights  -noMirror -surfaceAssociation closestPoint -influenceAssociation closestJoint;')



#######################################################################################################
''' intermediateObjectsCleanup 2013 '''################################################################
#######################################################################################################

def intermediateObjectsCleanup():
    '''- intermediateObjectsCleanup help
    
    Description:  Cleans up all intermediate objects in the scene 
    Dependencies: NONE
    Date:         06/10/2013
    Example:      intermediateObjectsCleanup()
    '''
    geometry = ['mesh', 'nurbsSurface', 'nurbsCurve']

    for each in geometry:

        mel.eval('select -r `listTransforms "-type %s"`;'%each)

        sl = mc.ls(sl=True)

        for s in sl:
            intObj = mc.ls(mc.listRelatives(s, shapes=True), intermediateObjects=True, type=each)
            
            if intObj:
                hisIntObj = mc.ls(mc.listHistory(s), intermediateObjects=True, type=each)

                if hisIntObj:
                    intObj.remove(hisIntObj[0])
                
                mc.delete(intObj)


#######################################################################################################
''' getPosListFromObjects 2015 ''' ####################################################################
#######################################################################################################

def getPosListFromObjects(inObjectList):
    '''- getNameListFromObjects help
    
    Description:  From a list of objects it returns a list of tuples with world space positions. 
                  Works on cvs, vertices and trasforms.
    Dependencies: NONE
    Date:         23/04/2015
    Example:      Select one various cvs, vertices or trasforms then run:
                  posList = getPosListFromObjects(mc.ls(sl=1, fl=1))
    '''
    posList = []

    for i, obj in enumerate(inObjectList):

        type = mc.objectType(obj)
        polyVertices = mc.filterExpand(obj, sm=31)
        surfCvs = mc.filterExpand(obj, sm=28)

        if type=='transform' or type=='joint' or type=='ikHandle':
            posList.append(tuple(mc.xform(obj, q=1, rp=1, ws=1)))

        elif surfCvs:
            if type == 'nurbsSurface':
                posList.append(tuple(mc.pointPosition(obj, world=1)))
            elif type == 'nurbsCurve':
                posList.append(tuple(mc.pointPosition(obj, world=1)))
            elif type == 'bezierCurve':
                posList.append(tuple(mc.pointPosition(obj, world=1)))
            else:
                mc.error('Selection is invalid!')

        elif polyVertices:
            posList.append(tuple(mc.pointPosition(obj, world=1)))
        
        elif type=='bezierCurve':
            posList.append(tuple(mc.pointPosition(obj, world=1)))
        else:
            mc.warning(type)
            mc.error('Selection is not valid! Select transforms or points.')


    return posList



#######################################################################################################
''' locatorAtSelection 2015 '''########################################################################
#######################################################################################################


def locatorAtSelection():
    '''- locatorAtSelection help
    
    Description:  From a 
    Dependencies: NONE
    Date:         23/04/2015
    Example:      tmp
                  
    '''
    sl = mc.ls(sl=1, fl=1)
    startLoc = mc.spaceLocator(n='pos_locator')[0]
    if sl:
        if '.' in sl[0]:
            mc.select(mc.polyListComponentConversion(sl, toVertex = True))
            cl = mc.cluster(n='cl', rel=True )[1]
            pos = mc.xform(cl, q=1, sp=1)
            mc.delete(cl)
            #mc.warning('Component!')
        else:
            pos = mc.xform(sl[0], query=True, worldSpace=True, rotatePivot=True)
            #mc.warning('Transform!')
            
        mc.move(pos[0], pos[1], pos[2], startLoc, rotatePivotRelative=True, worldSpace=True)
    mc.select(startLoc, r=1)
    
    return startLoc



#######################################################################################################
''' getNameListFromObjects 23/04/2015 '''##############################################################
#######################################################################################################

def getNameListFromObjects(inObjectList, padding=2):
    
    '''- getNameListFromObjects help
    
    Description:  From a list of objects it returns a list of indexes in padded string format. 
                  Works on cvs, vertices and trasforms.
    Dependencies: NONE
    Date:         23/04/2015
    Example:      Select one various cvs, vertices or trasforms then run:
                  getNameListFromObjects(mc.ls(sl=1, fl=1), padding=2)
    '''
    nameList = []

    for i, obj in enumerate(inObjectList):

        type = mc.objectType(obj)
        polyVertices = mc.filterExpand(obj, sm=31)
        surfCvs = mc.filterExpand(obj, sm=28)

        if type=='transform':
            nameList.append(str(i).rjust(padding, '0'))
            #nameList.append('%02d'%(i+1))

        elif surfCvs:
            if type == 'nurbsSurface':
                cvNum = obj.split('.cv')[-1]
                cvNum = cvNum.split('][')
                #add col and row with padding
                row = cvNum[0][1:].rjust(padding, '0')
                col = cvNum[1][:-1].rjust(padding, '0')
                rowCol =  (row + '_' + col)
                nameList.append(rowCol)

            elif type == 'nurbsCurve':
                cvNum = obj.split('.cv[')[-1]
                cvNum = cvNum.split(']')[0]
                num = cvNum.rjust(padding, '0')
                nameList.append(num)
                
            else:
                mc.error('Selection is invalid!')

        elif polyVertices:
            vtxNum = obj.split('[')[-1]
            vtxNum = vtxNum.split(']')[0]
            nameList.append(vtxNum.rjust(padding, '0'))
            
        else:
            mc.error('Selection is not valid! Select transforms or points.')

    return nameList
    
    
#######################################################################################################
''' createSurfaceFromEdgeLoops 2013 ''' ###############################################################
#######################################################################################################

def createSurfaceFromEdgeLoops(direction = 'right'):
    '''- createSurfaceFromEdgeLoops help
    
    Description:
        
        Creates a surface from a sequence o edge loops. Across the Z axis. 
        
        Dependencies:
            NONE
            
        Example:
            select one edge the run:
                createSurfaceFromEdgeLoops(direction = 'left')
    '''
    
    iniPos = []
    posList = []
    dir = direction
    #dir = 'left'
    firstSel = False
    x = 0
    j = ''

    edge = mc.ls(sl=1, fl=1)[0]
    mc.pickWalk (d=dir, type="edgeloop")
    ls = mc.ls(sl=1, fl=1)[0]
    mc.select(edge, r=1)

    while True:
        mc.pickWalk (d=dir, type="edgeloop")
        loop = mc.ls(sl=1, fl=1)

        if x != 0:
            if edge in loop:
                break

        if x==156:
            break

        mel.eval("PolySelectConvert 3;")
        cl = mc.cluster(n='cl', rel=True )[1]
        jPos = mc.xform(cl, q=1, sp=1)
        mc.delete(cl)

        if jPos in posList:
            break

        mc.select(loop, r=1)
        mc.pickWalk (d=dir, type="edgeloop")
        jPos[0] = 0.0
        posList.append(jPos)
        x += 1


    crv = mc.curve(p=posList, n='loopCenter_A_crv')
    dupCrv = mc.duplicate(crv, n='loopCenter_B_crv')
    mc.move(.1, 0, 0, crv, r=1, worldSpace=1)
    mc.move(-.1, 0, 0, dupCrv, r=1, worldSpace=1)
    mc.loft(crv, dupCrv, ch=0, u=1, c=0, ar=0, d=1, ss=1, rn=0, po=0, rsn=True, n='snk_guide_surf')
    mc.delete(crv, dupCrv)



#######################################################################################################
''' createJntChainFromSurfaceHulls 2013 WIP''' ########################################################
#######################################################################################################

def createJntChainFromSurfaceHulls(inSurface, direction = 'v'):
    '''- createJntChainFromSurfaceHulls help
    
    Description:
        
        Creates a Joint Chain From Surface Hulls
        
        Dependencies:
            getComponentSelectionPivot, chainFromPositionList
            
        Example:
            select nurbs surface the run:
                createJntChainFromSurfaceHulls()
    '''
    
    inObjectList = []
    #inSurface = mc.ls(sl=1)[0]
    #mc.warning('1')

    #Check if it's a list
    if type(inSurface) is not list:
        inObjectList.append(inSurface)
    else:
        inObjectList = inSurface

    surface = inObjectList[0]
    #mc.warning('2')

    shape = mc.listRelatives(surface, shapes=True)[0]
    degree = mc.getAttr('%s.degreeUV'%(shape))
    spans = mc.getAttr('%s.spansUV'%(shape))

    if direction=='v':
        
        hulls = degree[0][1] + spans[0][1]
        dirU = '[0:*]'

    elif direction=='u':
        
        hulls = degree[0][0] + spans[0][0]
        dirV = '[0:*]'
    else:
        mc.error('Incorrect direction flag!')

    posList = []
    #mc.warning('3')

    for i in range(hulls):
        
        if direction=='v':
            dirV = '[%s]'%i
        else:
            dirU = '[%s]'%i

        pos = getComponentSelectionPivot('%s.cv%s%s'%(surface, dirU, dirV))
        posList.append(pos)
    #mc.warning('4')

        
    return chainFromPositionList(posList)



def getComponentSelectionPivot(inComponents):
    
    mc.select(inComponents, r=True)
    #Create cluster
    tmpCl = mc.cluster(name='tmp_loc', relative=True )
    position = mc.xform(tmpCl[1], q=1, sp=1)
    mc.delete(tmpCl)
    
    return position


def chainFromPositionList(inPositionList):
    
    jointList = []
    mc.select(cl=True)
    for pos in inPositionList:
        j = mc.joint(p=(pos[0], pos[1], pos[2]), rad=1)
        mc.joint(j, edit=True, zeroScaleOrient=True, orientJoint='xyz', secondaryAxisOrient='yup')
        jointList.append(j)
    
    mc.joint(jointList[0], e=True, oj='xyz', secondaryAxisOrient='yup', children=True, zeroScaleOrient=True)
    
    #   Cleanup last joint
    if jointList[-1]:
        mc.setAttr("%s.jointOrientX"%jointList[-1], 0)
        mc.setAttr("%s.jointOrientY"%jointList[-1], 0)
        mc.setAttr("%s.jointOrientZ"%jointList[-1], 0)

    return jointList



def chain_from_surface(inSurfaceObj, direction='u', upVector=(0, 1, 0)):
    """ Creates a chain oriented by surface normals 
    Todo : add numOfJoints=10?
           add check if is an PyNode or a string 
    Usage : res = rlx.chain_from_surface(inSurfaceObj, direction='u', upVector=(0, 1, 0))
    OBS : inSurfaceObj is an pymel object!
    """

    chain = createJntChainFromSurfaceHulls(inSurfaceObj.name(), direction=direction)

    posList = getPosListFromObjects(chain)
    for i, j in enumerate(chain):#pass

        jnt = pm.PyNode(j)

        # --- Get pos
        if j == chain[-1]:
            pm.makeIdentity(jnt, jointOrient=1, apply=0)

        # Create tmp follicle
        fol =  follicle_to_closest_point(inSurfaceObj.name(), [posList[i]])[0]
        f = pm.PyNode(fol)
        # --- Set V to .5
        f.parameterV.set(.5)

        aim = pm.spaceLocator()
        up = pm.spaceLocator()

        #--- Position aim
        pm.parent(aim, jnt)
        pm.makeIdentity(aim, t=1, r=1, apply=0)
        aim.tx.set(10)

        #--- Position upv
        pm.parent(up, fol)
        pm.makeIdentity(up, t=1, r=1, apply=0)
        up.tz.set(10)

        pm.parent(aim, up, w=1)

        if not j == chain[-1]:
            child = jnt.getChildren()[0]
            pm.parent(child, w=1)
            off = pm.PyNode( createOffsetTransform(jnt.name()))
            acon = pm.aimConstraint(aim, off, aimVector=(1, 0, 0), upVector=upVector, worldUpType="object", worldUpObject=up)
            
            if j == chain[0]:
                pm.parent(jnt, w=1)
            else:
                pm.parent(jnt, off.getParent())

            pm.parent(child, jnt)

        else:
            off = pm.PyNode( createOffsetTransform(jnt.name()))
            acon = pm.aimConstraint(aim, off, aimVector=(1, 0, 0), upVector=upVector, worldUpType="object", worldUpObject=up)
            pm.delete(acon)
            pm.parent(jnt, off.getParent())

        pm.delete(off, aim, up, f.getParent())

    return chain


 
#######################################################################################################
''' toggleJointDrawStyle 2011 ''' #####################################################################
#######################################################################################################

def toggleJointDrawStyle(inJoints = mc.ls(sl = 1, type='joint')):
    '''- toggleJointDrawStyle help
    
    Description:
        
        Toggles JointDrawStyle22
        
        Dependencies:
            NONE
            
        Example:
            select joints, then run, or input a list of joints or string:
                sl = mc.ls(sl=1)
                toggleJointDrawStyle(sl[0])
    '''
    inObjectList = []

    #Check if it's a list
    if type(inJoints) is not list:
        inObjectList.append(inJoints)
    else:
        inObjectList = inJoints


    for s in inObjectList:

        curValue = mc.getAttr('%s.drawStyle'%s)

        if curValue==2:
            drawStyle = 0
            mc.setAttr('%s.drawStyle'%s, drawStyle )
        else:
            drawStyle = 2
            mc.setAttr('%s.drawStyle'%s, drawStyle )

#mc.warning(toggleJointDrawStyle.__doc__)

############################################################################################################
''' createCurveInSurfaceCenter 2011 ''' ####################################################################
############################################################################################################


def createCurveInSurfaceCenter(inSurface, coordinate='v', points=20, keepCurve=True):
    '''
    Description:
        
        Creates a cubic curve at the center of a nurbs surface and returns it's length
        
        Dependencies:
            NONE
            
        Example:
            select a nurbs surface then run:
                
                
                createCurveInSurfaceCenter(mc.ls(sl=1)[0], coordinate='v', points=50, keepCurve=True)
                sl = mc.ls(sl=1)
                createCurveInSurfaceCenter(
                                            inSurface, 
                                            coordinate='v', #Choose either "u" or "v" direction
                                            points=20, #Number of spans for the curve
                                            keepCurve=True #
                                            ) 
    '''
    posList = []

    step = 1.0/points

    for i in range(points+1):
        
        paramValue = i * step
        
        #mc.select(inSurface + '.%s[%s]'%(coordinate, paramValue))
        tmpCrv = mc.duplicateCurve(inSurface + '.%s[%s]'%(coordinate, paramValue), range=0, local=0, ch=0)[0]

        #center pivot
        mc.xform(tmpCrv, cp=True)
        pos = mc.xform(tmpCrv, q=True, rp=True, ws=True)
        posList.append(pos)
        
        #delete
        mc.delete(tmpCrv)


    crv = mc.curve(p=posList, n=inSurface + '_centerCurve')
    length = mc.arclen(crv)
    
    if keepCurve:
        return length, crv
    else:
        mc.delete(crv)
        return length


#################################################################################################################################
#
############################################################################################################################################
def attachBendToJoint(inBaseJoint, inEndJoint, inName, scale=1.0):
    '''
    Description:
        
        Attach ribbon control to selected start and end joints
        
        Dependencies:
            -getDistanceBetween()
            -snapToTarget()
            -parentShape()
            -old_proj_createCtrlShapes as ccs
            
        Example:
            select joint1 then joint2 and run:
                sl = mc.ls(sl=1)
                attachBendToJoint(sl[0], sl[1], 'inNames') 
    '''

    length = getDistanceBetween( inBaseJoint, inEndJoint )
    #old ribbon: topGrp, master, ctrlStart, ctrlEnd, test, ctrlLists = fsRbn.createRibbon(drivenSurface=False, name=inName, width=length, scale=.22, autoCtrlCurves=False, createOutMesh=False)
    
    
    snapToTarget(master, inBaseJoint, rotate=True)
    
    mc.parentConstraint(inBaseJoint, master, mo=0)
    
    #add curver to controls
    for i, layer in enumerate(ctrlLists):
        for j in layer:
            
            if i==0:
                shpCtrl = ccs.cube(scale=(scale*.003, scale*.075, scale*.075), color=29)
            
            elif i==1:
                shpCtrl = ccs.circle(scale=(scale*.0345, scale*.0345, scale*.0345), orientation=(0, 0,90))
                
            elif i==2:
                shpCtrl = ccs.circle(scale=(scale*.023, scale*.023, scale*.023), orientation=(0, 0,90), color=26)
                
            elif i==3:
                shpCtrl = ccs.locator(scale=(scale*.03, scale*.03, scale*.03), color=12)
                
            else:
                shpCtrl = ccs.cube(scale=(scale*.03, scale*.03, scale*.03))
            

            parentShape(shpCtrl, j)
    
    return master, ctrlStart, ctrlEnd, test, ctrlLists, topGrp
                
#################################################################################################################################
# Weighted version
############ ################################################################################################################################
def attachBendToJoint2(inBaseJoint, inEndJoint, inName, scale=1.0):
    '''
    Description:
        
        Attach ribbon control to selected start and end joints
        
        Dependencies:
            -getDistanceBetween()
            -snapToTarget()
            -parentShape()
            -old_proj_createCtrlShapes as ccs
            
        Example:
            select joint1 then joint2 and run:
                sl = mc.ls(sl=1)
                attachBendToJoint(sl[0], sl[1], 'inNames') 
    '''

    length = getDistanceBetween( inBaseJoint, inEndJoint )
    topGrp, master, ctrlStart, ctrlEnd, test, ctrlLists, tst2, tst3 = rb.createRibbon(drivenSurface=False, name=inName, width=length*.05, height=length, scale=.22, autoCtrlCurves=False, createOutMesh=False)
    
    
    snapToTarget(master, inBaseJoint, rotate=True)
    
    parent = mc.listRelatives(master, p=1)[0]
    
    #mc.parentConstraint(inBaseJoint, master, mo=0)
    mc.parentConstraint(inBaseJoint, parent, mo=0)
    
    #add curver to controls
    for i, layer in enumerate(ctrlLists):
        for j in layer:
            
            if i==0:
                shpCtrl = ccs.cube(scale=(scale*.003, scale*.075, scale*.075), color=29)
            
            elif i==1:
                shpCtrl = ccs.circle(scale=(scale*.0345, scale*.0345, scale*.0345), orientation=(0, 0,90))
                
            elif i==2:
                shpCtrl = ccs.circle(scale=(scale*.023, scale*.023, scale*.023), orientation=(0, 0,90), color=26)
                
            elif i==3:
                shpCtrl = ccs.locator(scale=(scale*.03, scale*.03, scale*.03), color=12)
                
            else:
                shpCtrl = ccs.cube(scale=(scale*.03, scale*.03, scale*.03))
            

            parentShape(shpCtrl, j)
    
    return master, ctrlStart, ctrlEnd, test, ctrlLists, topGrp
                


#################################################################################################################################
#  NOT DONE - addCtrlShapesToRibbon - WIP - Not implemented yet
############################################################################################################################################


def addCtrlShapesToRibbon(
                          inControlLists, 
                          overallScale=1.0, 
                          scale=[(0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3), (0.3, 0.3, 0.3)],
                          color=[13, 7, 12, 26, 13]
                          ):
    '''
    Description:
        
        This is made to be use with the module fs_old_proj_ribbon. It will add curve shapes to ribbon 
        control joints.
        
        Dependencies: 
            -parentShape()
            -old_proj_createCtrlShapes as ccs
            
        Example:
            Run createRibbon() then get the list of controls and run addCtrlShapesToRibbon:
                sl = fsRbn.createRibbon()[5]
                attachBendToJoint(sl[0], sl[1], 'inNames') 
    '''
    
    #add curver to controls
    for i, layer in enumerate(inControlLists):
        for j in layer:
            
            if i==0:
                shpCtrl = ccs.cube(scale=(.03 * overallScale, .03 * overallScale, .03 * overallScale), color=13)
            
            elif i==1:
                shpCtrl = ccs.prism(scale=(.08 * overallScale, .03 * overallScale, .08 * overallScale), orientation=(0, 0,90))
                
            elif i==2:
                shpCtrl = ccs.locator(scale=(.03 * overallScale, .03 * overallScale, .03 * overallScale), color=12)
                
            elif i==3:
                shpCtrl = ccs.circle(scale=(.03 * overallScale, .03 * overallScale, .03 * overallScale), orientation=(0, 0,90), color=26)
            else:
                shpCtrl = ccs.cube(scale=(.03 * overallScale, .03 * overallScale, .03 * overallScale))
            

            parentShape(shpCtrl, j)

############################################################################################################################################
#Duplicate and rename hierarchy - 2011
############################################################################################################################################

def duplicateRenameChain(inBaseJ, inSuffix):
    '''
    Description:
        
        Duplicate and rename hierarchy. Returns a list with the new hierarchy
        
        Dependencies: 
            NONE
            
        Example:
            ikChainJoints = duplicateRenameChain('hmn_leg_01_jnt', 'ik')
                // Result: u'hmn_leg_01_ik_jnt' //
    '''
    newChain = []

    #Get all original names
    mc.select(inBaseJ, hi=1)
    oriJs = mc.ls(sl=True, type='joint')

    #duplicate
    dupJs = mc.duplicate(inBaseJ, renameChildren=True)

    #Rename it
    for ori, dup in zip(oriJs, dupJs):
        
        if 'jnt' in ori:
            newName = ori.replace('jnt', inSuffix + '_jnt')
        else:
            newName = ori + '_' + inSuffix
        
        mc.rename(dup, newName)
        newChain.append(newName)

    return newChain


############################################################################################################################################
#Straighten Joint Chain 2011
############################################################################################################################################

def straightenJointChain(jointList, direction='-y', behavior=False, worldCenter=False):
    '''
    Description:
        
        From the current selected joint chain, recreate it in a straight line on the direction indicated.
        Returns a list with the new joints
        
        Dependencies: 
            -duplicateRenameChain()
            -getDistanceBetween()
            
        Example:
            straightenJointChain(
            jointList, 
            direction='-y', 
            behavior=False, #For mirror behavior
            worldCenter=False #base joint at the center of the world
            ) 
    '''
    jnt = []
    numOfJs = len(jointList)
    jLength = [0.00]
    
    #Define pos or neg sign
    if '+' in direction:
        sign = 1
    elif '-' in direction:
        sign = -1
    else:
        mc.error('Direction flag has a problem with the sign')

    #Define axis
    if 'x' in direction:
        axis = '.tx'
    elif 'y' in direction:
        axis = '.ty'
    elif 'z' in direction:
        axis = '.tz'
    else:
        mc.error('Direction flag has a problem with the axis')
    
    #duplicate and rename chain
    oriJs = duplicateRenameChain(jointList[0], 'Ori')
    mc.delete(jointList)

    #Recreate skeleton on a straight line
    for i in range(0, numOfJs-1):
        jLength.append(getDistanceBetween(oriJs[i], oriJs[i+1]))

    if worldCenter:
        startPos = (0, 0, 0)
    else:
        startPos = mc.xform(oriJs[0], query=True, worldSpace=True, rotatePivot=True)

    mc.select(cl=1)

    for i, j in enumerate(oriJs):
        jnt.append(mc.joint(p=(startPos[0], startPos[1], startPos[2]), radius=0.01, name=j.replace('_Ori', '')))
        if not i==0:
            if behavior:
                mc.setAttr(jnt[i] + axis, sign*-jLength[i])
                mc.joint(jnt[i-1], e=True, orientJoint='xyz', secondaryAxisOrient='yup')
                mc.setAttr(jnt[i]+'.tx', -jLength[i])
            else:

                mc.setAttr(jnt[i] + axis, sign*jLength[i])

                mc.joint(jnt[i-1], e=True, orientJoint='xyz', secondaryAxisOrient='yup')

    if behavior:
        mc.setAttr(jnt[0]+'.jointOrientX', -180.00)

    #return a list with the new joints
    return jnt

#sl = mc.ls(sl=1, type='joint')
#straightenJointChain(sl, direction='-y', behavior=False, worldCenter=False)
############################################################################################################################################
#Get Distance Between 2011
############################################################################################################################################
def getDistanceBetween( strObjectA, strObjectB ):
    '''
    Description:
        
        Returns the distance between two objs
        
        Dependencies: 
            -calculateDistanceBetween()
    '''
    WSPosA = mc.xform(strObjectA, q=True, ws=True, t=True)
    WSPosB = mc.xform(strObjectB, q=True, ws=True, t=True)

    #return the distance between the two points
    return calculateDistanceBetween( WSPosA[0], WSPosA[1], WSPosA[2], WSPosB[0], WSPosB[1], WSPosB[2] )


#Calculates the distance between two vectors
def calculateDistanceBetween(posAx, posAy, posAz, posBx, posBy, posBz):
    dx = posAx - posBx
    dy = posAy - posBy
    dz = posAz - posBz
    
    return(math.sqrt( dx*dx + dy*dy + dz*dz ))



############################################################################################################################################
#Setup IKFK Blend 2011
############################################################################################################################################

def setupIKFKBlend(jointList, switch):
    '''
    Description:
        
        Creates a blend setup chain. Ikfk attribute will be added to given switch control node
        Returns a list with the new ik and fk joint chains
        
        Dependencies: 
            -duplicateRenameChain()
            -blendAttrSetup()
            
        Example:
            setupIKFKBlend(
                            jointList, #Joint chain 
                            switch #Switch control
                            )
    '''
    #Add objectsB attr
    attr = 'IK_FK'
    mc.addAttr(switch, ln=attr, at='enum', en='FK:IK:')
    mc.setAttr(switch + '.' + attr, e=True, keyable=True)


    fk = duplicateRenameChain(jointList[0], 'fk')
    ik = duplicateRenameChain(jointList[0], 'ik')
    
    blndNodes = blendAttrSetup(objectsA=ik, objectsB=fk, drivenObject=jointList)
    
    for blnd in blndNodes:
        mc.connectAttr(switch + '.' + attr, blnd + '.blender')

    return ik, fk


def blendAttrSetup(objectsA, objectsB, drivenObject):
    '''
    Description:
        
        Create blend connection from two lists of objects into one list of driven objects
        Returns a list with the blend color nodes
        
        Dependencies: 
            NONE
    '''
    blendNodes = []
    attrs = ['.translate', '.rotate', '.scale']
    
    for att in attrs:
        for i in range(0, len(objectsA)):
            blndTr = mc.createNode('blendColors', n=objectsA[i] + '_blndColors')
            blendNodes.append(blndTr)

            mc.connectAttr(objectsA[i] + att, blndTr + '.color1')
            mc.connectAttr(objectsB[i] + att, blndTr + '.color2')
            mc.connectAttr(blndTr + '.output', drivenObject[i] + att)


    return blendNodes


############################################################################################################################################
#Create Control For Target 2011
############################################################################################################################################

def createControlForTarget(inCtrl, inTarget, maintainOffset=False):
    '''
    Description:
        
        Sets up a control curve to target object with basic control hierarchy
        Returns the top group
        
        Dependencies: 
            NONE
            
        Example:
            createControlForTarget(
                            inCtrl, 
                            inTarget,
                            maintainOffset=False,
                            )
    '''


    if not maintainOffset:
        pos = mc.xform(inTarget, query=True, worldSpace=True, rotatePivot=True)
        mc.move(pos[0], pos[1], pos[2], inCtrl, rotatePivotRelative=True)                      
        mc.makeIdentity(inCtrl, rotate=True, translate=True, scale=True, apply=True)

    off = mc.duplicate(inCtrl, po=True, n=inCtrl + '_offset')[0]
    zero = mc.duplicate(inCtrl, po=True, n=inCtrl + '_zero')[0]
    grp = mc.duplicate(inCtrl, po=True, n=inCtrl + '_grp')[0]

    mc.parent(off, zero)
    mc.parent(zero, grp)
    mc.parent(inCtrl, off)
    mc.parent(inTarget, inCtrl)
    
    return grp


############################################################################################################################################
''' Snap To Target 2010 '''
############################################################################################################################################

def snapToTarget(inObject, inTarget, offset=(0, 0, 0), rotate=False):
    '''
    Description:
        
        Move and orient object to target.
        
        Dependencies: 
            getPosListFromObjects()
            
        Example:
            ikChainJoints = snapToTarget(locator, ik, offset=(0, 0.02, -0.085), rotate=True)
    '''
    #Get values
    #pos = mc.xform(inTarget, query=True, worldSpace=True, rotatePivot=True)
    pos = getPosListFromObjects([inTarget])[0]

    #Set values
    mc.move(pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2], inObject, rotatePivotRelative=True)
    
    if rotate:
        rot = mc.xform(inTarget, query=True, worldSpace=True, rotation=True)
        mc.xform(inObject, worldSpace=True, rotation=(rot[0], rot[1], rot[2]))


############################################################################################################################################
#Set Joint Draw Style 2010
############################################################################################################################################

def setJointDrawStyle(inJntList, drawStyle = 2):
    """Usage : 
        inJntList = mc.ls(sl=1, type='joint')
        rlx.setJointDrawStyle(inJntList, drawStyle = 2)"""
    for j in inJntList:
        mc.setAttr( j + '.drawStyle', drawStyle )


############################################################################################################################################
#Get String Before Padding 2011
############################################################################################################################################
def getStringBeforePadding(inObject):
    '''
    Description:
        
        Get the first part of the string, before the padding numbers.
        
        Dependencies: 
            NONE
            
        Example:
            string = getStringBeforePadding('hmn_leg_01_jnt')
            // Result: 'hmn_leg_' //
    '''
    breakPoint = ''
    for each in inObject:
        if each.isdigit():
            breakPoint = each
            break 
    if breakPoint:
        name = inObject.split(breakPoint)[0]
        print name
    else:
        name = False

    return name


############################################################################################################################################
#Lock And Hide Attributtes 2010
############################################################################################################################################
def lockAndHideAttrs(inVariable, v=True, t=False, r=False, s=False, radi=False, all=False):
    '''
    Description:
        Lock And Hide transform node attributtes.
        Dependencies:
            NONE
        Example:
            lockAndHideAttrs(mc.ls(sl=1), all=1)
            lockAndHideAttrs(mc.ls(sl=1), radi=1, v=0)
    '''
    # --- Make force inVariable to be of type list
    inObjList = force_return_list(inVariable)
    # --- Sort attrs
    attrList = []

    if radi or all:
        attrList.extend(['.radius'])
    if v or all:
        attrList.extend(['.v'])
    if t or all:
        attrList.extend(['.tx', '.ty', '.tz'])
    if r or all:
        attrList.extend(['.rx', '.ry', '.rz'])
    if s or all:
        attrList.extend(['.sx', '.sy', '.sz'])

    for each in inObjList:
        
        #Visibility
        for attr in attrList:
            if attr=='.radius' and mc.objectType(each)!='joint':
                continue

            elif not mc.getAttr(each + attr, lock=True):
                if attr=='.v':
                    mc.setAttr(each + attr, 0, lock=True)
                else:
                    mc.setAttr(each + attr, lock=True)
            
            mc.setAttr(each + attr, e=1, k=False, cb=False)


def force_return_list(inVariable):
    if isinstance(inVariable, list):
        inNodeList = inVariable

    elif isinstance(inVariable, tuple):
        inNodeList = inVariable

    elif isinstance(inVariable, dict):
        mc.error("its a dictionary. Input variable can't be of type dict.")

    else:
        inNodeList = [inVariable]

    return inNodeList


############################################################################################################################################
#Connect visibility on a switch 2010
############################################################################################################################################
def connectSwitchViz(inOffList, inOnList, switchAttr):
    '''
    Description:
        
        Connect visibility to a on/off switch control.
        
        Dependencies: 
            NONE
            
        Example:
            #add visibiliity switch to ikfk controlls
            ikCtrlList = mc.ls(sl=1)
			FKControlList = mc.ls(sl=1)
			switch = mc.ls(sl=1)[0]
			connectSwitchViz(FKControlList, ikCtrlList, switch + '.IK_FK')
    '''
    for each in inOnList:
        mc.connectAttr(switchAttr, each + '.v')
    for each in inOffList:
        rev = mc.createNode('reverse', n=each + '_onOff_reverse')
        mc.connectAttr(switchAttr, rev + '.input.inputX')
        mc.connectAttr( rev + '.output.outputX', each + '.v')

#ikCtrlList = mc.ls(sl=1)
#FKControlList = mc.ls(sl=1)
#switch = mc.ls(sl=1)[0]
#connectSwitchViz(FKControlList, ikCtrlList, switch + '.IK_FK')

############################################################################################################################################
#Create On Plane Follicle 2010
############################################################################################################################################
def handdleForSkinCluster(inObj=(mc.ls(sl=1)), scale=0.05, name='pin', rotation=True):
    '''
    Description:
        
        Creates a linear nurbs plane with a follicle on it's center. Returns follicle transform node.
        
        Dependencies: 
            -snapToTarget()
    '''
    inObject = inObj[0]
    description = "skinAttach"
    
    
    if not rotation:

        #Create curve

        crv = mc.curve(degree=1, p=[(-1*scale, 0, 0), (1*scale, 0, 0)], n='%s_%s_crv'%(name, description))
        shape = mc.listRelatives(crv, shapes=True)[0]
        snapToTarget(crv, inObject)

        #name = s.replace ("_LOC" , "_PCI")

        pointOCI = mc.createNode ("pointOnCurveInfo" , n = '%s_%s_pointOnCurveInfo'%(name, description))
        mc.connectAttr('%s.worldSpace'%shape , '%s.inputCurve'%pointOCI)
        mc.setAttr('%s.parameter'%pointOCI , .5 )
        loc = mc.spaceLocator(n='%s_%s_loc'%(name, description))[0]
        mc.connectAttr(pointOCI + '.position' , '%s.t'%loc)
        
        return loc
        
        
    else:
        
        surface = mc.nurbsPlane(patchesU=0, patchesV=0, width=scale, constructionHistory=False, name=name + '_surface')[0]

        snapToTarget(surface, inObject)

        #Create linear first to get the right spacing
        mc.rebuildSurface(
                          surface,
                          constructionHistory=0,
                          replaceOriginal=1,
                          rebuildType=0,
                          endKnots=1,
                          keepRange=0,
                          keepControlPoints=0,
                          keepCorners=0,
                          spansU=1,
                          degreeU=1,
                          spansV=1,
                          degreeV=1,
                          tolerance=0,
                          fitRebuild=0,
                          direction=2
                          )

        #Create follicle grp
        folP = '%s_%s_follicles_grp'%(name, description)
        if not(mc.objExists(folP)):
            folP = mc.createNode('transform', n=folP )

        #Create follicle transform and shape
        fol = mc.createNode('transform', n = '%s_%s_follicle_node'%(name, description), p = folP )
        fols = mc.createNode('follicle', n = '%s_%s_follicle_nodeShape'%(name, description), p = fol )
        #Connect to surface
        mc.connectAttr(surface + '.worldMatrix[0]', fols + '.inputWorldMatrix')
        mc.connectAttr(surface + '.local', fols + '.inputSurface')
        mc.connectAttr(fols + '.outTranslate', fol + '.translate')
        mc.connectAttr(fols + '.outRotate', fol + '.rotate')

        mc.setAttr(fols + '.parameterU', .5)
        mc.setAttr(fols + '.parameterV', .5)
        
        return fol



############################################################################################################################################
#Create stretch ik 2011
############################################################################################################################################


def createStretch(inJointChainList, stretchMode='translation', name='stretchy_rig', axis='x', straightChain=True):
    '''
    Description:
        
        Create stretchy ik.
        
        Dependencies: 
            NONE
            
        Example:
            stretchList = createStretch(ikZChain, 
                                        stretchMode='translation', 
                                        name=jntA.replace('01_jnt', 'ik_stretchy_rig')
                                        )
    '''
    inStart = inJointChainList[0]
    inEnd = inJointChainList[-1]

    posStart = mc.xform(inStart, query=True, worldSpace=True, rotatePivot=True)
    posEnd = mc.xform(inEnd, query=True, worldSpace=True, rotatePivot=True)

    #Create linea curve
    curveDeform = mc.curve(degree=1, point=[(posStart[0], posStart[1], posStart[2]), (posEnd[0], posEnd[1], posEnd[2])], n=name + '_def_crv')
    curveLength = mc.curve(degree=1, point=[(posStart[0], posStart[1], posStart[2]), (posEnd[0], posEnd[1], posEnd[2])], n=name + '_length_crv')

    #Create joints to drive the curve
    mc.select(clear=True)
    startJ = mc.joint(position=(posStart[0], posStart[1], posStart[2]), n=name + '_start_jnt')
    mc.select(clear=True)
    endJ = mc.joint(position=(posEnd[0], posEnd[1], posEnd[2]), n=name + '_end_jnt')
    mc.select(clear=True)

    #bind
    skin = mc.skinCluster(startJ, endJ, curveDeform, dr=4.5, maximumInfluences=1, frontOfChain=1, toSelectedBones=1, n=name + '_skC')

    #for crv in [curveDeform, curveLength]:
    #defCrvLen = mc.createNode('arclength', n='test')
    defCrvLen = mc.rename(mc.arclen(curveDeform, constructionHistory=True), name + '_curveInfo')
    oriCrvLen = mc.arclen(curveLength, constructionHistory=True)

    #Create MD node
    md = mc.createNode('multiplyDivide', n=name + '_multiplyDivide')

    #Connect attr
    mc.connectAttr(defCrvLen + '.arcLength', md + '.input1X')
    mc.connectAttr(oriCrvLen + '.arcLength', md + '.input2X')

    #Set to divide
    mc.setAttr(md + '.operation', 2)


    #Create node switch
    cond = mc.createNode('condition')
    mc.setAttr(cond + '.operation', 2)
    mc.connectAttr(defCrvLen + '.arcLength', cond + '.firstTerm')
    mc.connectAttr(oriCrvLen + '.arcLength', cond + '.secondTerm')

    mc.connectAttr(md + '.outputX', cond + '.colorIfTrueR')


    #plug normalized value
    if stretchMode=='translation':
        for j in inJointChainList[1:]:
            mc.warning(j)
            
            #Create multiply node
            mdJ = mc.createNode('multiplyDivide')
            #Get current tx value
            jntTX = mc.getAttr('%s.t%s' % (j, axis))
            mc.setAttr(mdJ + '.input2X', jntTX)
            
            
            mc.connectAttr(cond + '.outColorR', mdJ + '.input1X')
            
            mc.connectAttr(mdJ + '.outputX', '%s.t%s' % (j, axis))
    else:
        for j in inJointChainList[:-1]:
            mc.warning(j)
            
            #Create multiply node
            mdJ = mc.createNode('multiplyDivide')
            #Get current tx value
            #jntTX = mc.getAttr('%s.t%s' % (j, axis))
            #mc.setAttr(mdJ + '.input2X', jntTX)
            
            
            mc.connectAttr(cond + '.outColorR', mdJ + '.input1X')
            
            mc.connectAttr(mdJ + '.outputX', '%s.s%s' % (j, axis))
            
    if not straightChain:
        lenSum = getChainLength(inJointChainList)
        mc.move(0, 0, 0, '%s.cv[0]'%curveLength, worldSpace=True)
        mc.move(0, lenSum, 0, '%s.cv[1]'%curveLength, worldSpace=True)

    return startJ, endJ, curveDeform, curveLength, defCrvLen


def createSplineStretch(inJointChainList, inCurve, axis='x', stretchMode='translation', name='stretchy_rig', straightChain=True):
    '''
    Description:
        
        Create stretchy ik.
        
        Dependencies: 
            NONE
            
        Example:
            stretchList = createStretch(ikZChain, 
                                        stretchMode='translation', 
                                        name=jntA.replace('01_jnt', 'ik_stretchy_rig')
                                        )
    '''
    inStart = inJointChainList[0]
    inEnd = inJointChainList[-1]

    posStart = mc.xform(inStart, query=True, worldSpace=True, rotatePivot=True)
    posEnd = mc.xform(inEnd, query=True, worldSpace=True, rotatePivot=True)

    #Create linea curve
    curveDeform = inCurve
    defCrvLen = mc.rename(mc.arclen(curveDeform, constructionHistory=True), name + '_curveInfo')
    crvLen = mc.getAttr(defCrvLen + '.arcLength')

    curveLength = mc.curve(degree=1, point=[(0, 0, 0), (0, crvLen, 0)], n=name + '_spline_length_crv')

    #curveLength = mc.duplicate(inCurve, n=name + '_length_crv')[0]#  mc.curve(degree=1, point=[(posStart[0], posStart[1], posStart[2]), (posEnd[0], posEnd[1], posEnd[2])], n=name + '_length_crv')

    oriCrvLen = mc.arclen(curveLength, constructionHistory=True)

    #Create MD node
    md = mc.createNode('multiplyDivide', n=name + '_multiplyDivide')

    #Connect attr
    mc.connectAttr(defCrvLen + '.arcLength', md + '.input1X')
    mc.connectAttr(oriCrvLen + '.arcLength', md + '.input2X')

    #Set to divide
    mc.setAttr(md + '.operation', 2)


    #plug normalized value
    if stretchMode=='translation':
        for j in inJointChainList[1:]:
            mc.warning(j)
            
            #Create multiply node
            mdJ = mc.createNode('multiplyDivide')
            #Get current tx value
            jntTX = mc.getAttr('%s.t%s' % (j, axis))
            mc.setAttr(mdJ + '.input2X', jntTX)
            
            
            mc.connectAttr(md + '.outputX', mdJ + '.input1X')
            
            mc.connectAttr(mdJ + '.outputX', '%s.t%s' % (j, axis))
    else:
        for j in inJointChainList[:-1]:
            mc.warning(j)
            
            #Create multiply node
            mdJ = mc.createNode('multiplyDivide')
            #Get current tx value
            #jntTX = mc.getAttr('%s.t%s' % (j, axis))
            #mc.setAttr(mdJ + '.input2X', jntTX)
            
            
            mc.connectAttr(md + '.outputX', mdJ + '.input1X')
            
            mc.connectAttr(mdJ + '.outputX', '%s.s%s' % (j, axis))
            


    return curveDeform, curveLength


def getChainLength(inJointChainList):

    totalDist = 0.00
    for i, j in enumerate(inJointChainList):
        if j != inJointChainList[-1]:
            dist = getDistanceBetween(j, inJointChainList[i+1])
            totalDist += dist
    
    return totalDist


############################################################################################################################################
''' Panrent Shape 2010 '''
############################################################################################################################################

def parentShape(inShapeObj, inTarget, maintainPos=False):
    '''
    Description:
        
        Parent shape nodes to target objects.
        Dependencies:
            NONE
    '''
    # Create a temp grp to hold the shapes just in case it's a joint
    grp = mc.group(em=1)
    mc.parent(grp, inShapeObj)
    mc.makeIdentity(grp, apply=maintainPos, t=True, r=True, s=True)
    mc.parent(grp, w=True)

    shapes = []
    for s in mc.listRelatives (inShapeObj, shapes=True):
        newShape = mc.rename(s, inTarget + 'Shape_1')
        shapes.append(newShape)
    mc.parent(shapes, grp, r=True, s=True)

    mc.parent(grp, inTarget)
    mc.makeIdentity(grp, apply=maintainPos, t=True, r=True, s=True)
    mc.parent(grp, w=True)

    shapes = []
    for s in mc.listRelatives (grp, shapes=True):
        newShape = mc.rename(s, inTarget + 'Shape_1')
        shapes.append(newShape)
    mc.parent(shapes, inTarget, r=True, s=True)

    #Delete old grp
    mc.delete(inShapeObj, grp)


#######################################################################################################
''' delShapes  2015 ''' ###############################################################################
#######################################################################################################


def delShapes(inTransform):
    '''- getNameListFromObjects help
    
    Description:  Deletes all shapes from transform.
    Dependencies: NONE
    Date:         23/04/2015
    Example:      delShapes(inTransform)
    '''
    shapes = mc.listRelatives(inTransform, s=True)
    if shapes:
        for s in shapes:
            mc.delete(s)

############################################################################################################################################
#Create Driver Control
############################################################################################################################################

def createDriverCtrl(inObject, suffix='ctrl'):
    '''
    Description:
        
        Creates a driver control with constraints for the object.
        
        Dependencies: 
            createOffsetTransform()
    '''
    ctrl = mc.duplicate(inObject, parentOnly=True, n=inObject + '_' + suffix)[0]
    offset = createOffsetTransform(ctrl)
    mc.parentConstraint(ctrl, inObject, mo=True)
    mc.scaleConstraint(ctrl, inObject, mo=True)
    
    return ctrl, offset


############################################################################################################################################
#Create Offset Transform
############################################################################################################################################

def createOffsetTransform(inObject, name=''):
    '''
    Description:
        
        Creates a duplicated object to work as an offset node on top of the original object.
        
        Dependencies: 
            NONE
        TODO:
        Create option to enter a list of suffixes
        #inSuffixList = ['cns', 'offset', 'zero']
        #def create_offset_transform(inObject, inSuffixList, name=None):
    '''
    if not name:

        if '_offset' in inObject:
            newName = inObject.replace('_offset', '_zero')
        elif '_zero' in inObject:
            newName = inObject.replace('_zero', '_grp')
        elif '_jnt' in inObject:
            newName = inObject.replace('_jnt', '_offset')
        elif '_bind' in inObject:
            newName = inObject.replace('_bind', '_offset')
        elif '_ctrl' in inObject:
            newName = inObject.replace('_ctrl', '_ct_offset')
        elif '_grp' in inObject:
            newName = inObject.replace('_grp', '_offset')
        elif '_surface' in inObject:
            newName = inObject.replace('_surface', '_offset')
        elif '_loc' in inObject:
            newName = inObject.replace('_loc', '_offset')
        elif '_geo' in inObject:
            newName = inObject.replace('_geo', '_offset')
        else:
            newName = inObject + '_offset'
    else:
        newName = name
    
    dup = mc.duplicate(inObject, po=True, n=newName)[0]
    mc.parent(inObject, dup)
    
    return dup

