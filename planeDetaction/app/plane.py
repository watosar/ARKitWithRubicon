from rubicon.objc import *
from rubicon.objc.runtime import load_library, send_super, c_void_p
import math
from pathlib import Path

load_library('ARKit')
SCNNode = ObjCClass('SCNNode')
SCNPlane = ObjCClass('SCNPlane')
ARPlaneAnchor = ObjCClass('ARPlaneAnchor')
ARSCNPlaneGeometry = ObjCClass('ARSCNPlaneGeometry')
UIColor = ObjCClass('UIColor')
# Convenience extension for colors defined in asset catalog.
'''
extension UIColor {
    static let planeColor = UIColor(named: "planeColor")!
}'''

Vec3 = types.ctype_for_encoding(b'{Vec3=fff}')


class Plane(SCNNode):
    meshNode = objc_property()
    extentNode = objc_property()
    classificationNode = objc_property()
    
    # - Tag: VisualizePlane
    @objc_method
    def initWithAnchor_sceneView_(self, anchor, sceneView):
        # Create a mesh to visualize the estimated shape of the plane.
        
        meshGeometry = ARSCNPlaneGeometry.planeGeometryWithDevice_(sceneView.device)
        if not meshGeometry: raise RuntimeError('cant create plane')
        
        meshGeometry.updateFromPlaneGeometry_(anchor.geometry)
        self.meshNode = SCNNode.nodeWithGeometry_(meshGeometry)
        
        # Create a node to visualize the plane's bounding rectangle.
        t = repr(anchor)
        x, _, z = (CGFloat(float(i)) for i in t[t.find('extent')+8:-3].split())
        plane = SCNPlane.planeWithWidth_height_(x, z)
        extentPlane = plane
        self.extentNode = SCNNode.nodeWithGeometry_(extentPlane)
        center = tuple(
            float(i) 
            for i in t[t.find('center')+8:].split(')')[0].split()
        )
        self.extentNode.position = center
        
        # `SCNPlane` is vertically oriented in its local coordinate space, so
        # rotate it to match the orientation of `ARPlaneAnchor`.
        self.extentNode.eulerAngles = (-math.pi/2,-0.0,0.0)
        
        self = ObjCInstance(send_super(__class__, self, 'init'))
        
        self.setupMeshVisualStyle()
        self.setupExtentVisualStyle()

        # Add the plane extent and plane geometry as child nodes so they appear in the scene.
        self.addChildNode_(self.meshNode)
        self.addChildNode_(self.extentNode)
        
        # Display the plane's classification, if supported on the device
        if ARPlaneAnchor.isClassificationSupported():
            classification = anchor.classification.description
            textNode = self.makeTextNode_(classification)
            self.classificationNode = textNode
            # Change the pivot of the text node to its center
            textNode.centerAlign()
            # Add the classification node as a child node so that it displays the classification
            self.extentNode.addChildNode_(textNode)
        
        return self
    
    @objc_method
    def setupMeshVisualStyle(self) -> None:
        # Make the plane visualization semitransparent to clearly show real-world placement.
        self.meshNode.opacity = 0.25
        
        # Use color and blend mode to make planes stand out.
        material = self.meshNode.geometry.firstMaterial
        material.diffuse.contents = UIColor.grayColor
    
    @objc_method
    def setupExtentVisualStyle(self) -> None:
        # Make the extent visualization semitransparent to clearly show real-world placement.
        self.extentNode.opacity = 0.6

        material = self.extentNode.geometry.firstMaterial
        material.diffuse.contents = UIColor.grayColor

        # Use a SceneKit shader modifier to render only the borders of the plane.
        shader = ns_from_py((Path(__file__).parent/'Assets.scnassets/wireframe_shader.metal').read_text(encoding='utf-8'))
        SCNShaderModifierEntryPointSurface = ObjCInstance(runtime.c_void_p.in_dll(runtime.CDLL(None), 'SCNShaderModifierEntryPointSurface'))
        material.shaderModifiers = NSDictionary.dictionaryWithObject_forKey_(shader, SCNShaderModifierEntryPointSurface)
    
    @objc_method
    def makeTextNode_(self, text):
        textGeometry = SCNText.textWithString_extrusionDepth_(text, 1)
        textGeometry.font = UIFont.fontWithName_size_(ns_from_py("Futura"), 75)

        textNode = SCNNode.nodeWithGeometry_(textGeometry)
        # scale down the size of the text
        textNode.scale = (0.0005,)*3
        
        return textNode
