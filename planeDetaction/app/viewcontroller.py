from rubicon.objc import *
from rubicon.objc.runtime import load_library, send_super
from .plane import Plane
from pathlib import Path
import objc_util

load_library('UIKit')
load_library('SceneKit')
load_library('ARKit')

#ARSCNViewDelegate = ObjCProtocol('ARSCNViewDelegate')
ARSessionDelegate = ObjCProtocol('ARSessionDelegate')

UIViewController = ObjCClass('UIViewController')
UIView = ObjCClass('UIView')
UIVisualEffectView = ObjCClass('UIVisualEffectView')
UIBlurEffect = ObjCClass('UIBlurEffect')
UILabel = ObjCClass('UILabel')
ARSCNView = ObjCClass('ARSCNView')
ARWorldTrackingConfiguration = ObjCClass('ARWorldTrackingConfiguration')
UIApplication = ObjCClass('UIApplication')
ARCamera = ObjCClass('ARCamera')
SCNScene = ObjCClass('SCNScene')
NSURL = ObjCClass('NSURL')

UIViewContentModeScaleAspectFill = 2

ARPlaneDetectionHorizontal = (1 << 0)
ARPlaneDetectionVertical = (1 << 1)

UIAlertControllerStyleAlert = 1
UIAlertActionStyleDefault = 0

ARSessionRunOptionResetTracking = (1 << 0)
ARSessionRunOptionRemoveExistingAnchors = (1 << 1)

ARTrackingStateNotAvailable = 0
ARTrackingStateLimited = 1
ARTrackingStateNormal = 2

ARTrackingStateReasonNone = 0
ARTrackingStateReasonInitializing = 1
ARTrackingStateReasonRelocalizing = 2
ARTrackingStateReasonExcessiveMotion = 3
ARTrackingStateReasonInsufficientFeatures = 4

class MyViewController(UIViewController, protocols=[ARSessionDelegate]):
    @objc_method
    def init(self):
        self = ObjCInstance(send_super(__class__, self, 'init'))
        frame = CGRect((0,0),(375,667))
        
        self.view.initWithFrame_(frame)
        self.sceneView = ARSCNView.alloc().initWithFrame_(frame)
        self.sceneView.delegate = self
        self.sceneView.scene = SCNScene.sceneWithURL_options_(NSURL.fileURLWithPath_(str(Path(__file__).parent/'Assets_scnassets/CameraSetup.scn')),None)
        self.view.addSubview_(self.sceneView)
        
        self.sessionInfoView = UIVisualEffectView.alloc().initWithEffect_(UIBlurEffect.effectWithStyle_(1))
        self.sessionInfoView.setOpaque_(False)
        self.sessionInfoView.setFrame_(CGRect((15, 596),(191, 38)))
        self.view.addSubview_(self.sessionInfoView)
        
        contentView = self.sessionInfoView.contentView
        contentView.setOpaque_(False)
        contentView.contentMode = 4
        
        self.sessionInfoLabel = UILabel.alloc().initWithFrame_(CGRect((8,8),(169,22)))
        self.sessionInfoLabel.setOpaque_(False)
        self.sessionInfoLabel.setUserInteractionEnabled_(False)
        self.sessionInfoLabel.setContentHuggingPriority_forAxis_(251,0)
        self.sessionInfoLabel.setContentHuggingPriority_forAxis_(251,1)
        self.sessionInfoLabel.setNumberOfLines_(0)
        self.sessionInfoLabel.setText_(ns_from_py('Initializing AR session.'))
        contentView.addSubview_(self.sessionInfoLabel)
        
        return self
    
    # start ar session
    @objc_method
    def viewDidAppear_(self, animated: types.c_bool) -> None:
        print('appear')
        send_super(__class__, self, 'viewDidAppear:', animated)
        
        # Start the view's AR session with a configuration that uses the rear camera,
        # device position and orientation tracking, and plane detection.
        configuration = ARWorldTrackingConfiguration.new()
        configuration.planeDetection = \
            ARPlaneDetectionHorizontal | ARPlaneDetectionVertical
        self.sceneView.session.runWithConfiguration_(configuration)

        # Set a delegate to track the number of plane anchors for providing UI feedback.
        self.sceneView.session.delegate = self
        
        #Prevent the screen from being dimmed after a while as users will likely
        #have long periods of interaction without touching the screen or buttons.
        UIApplication.sharedApplication.setIdleTimerDisabled_(True)
        
        # Show debug UI to view performance metrics (e.g. frames per second).
        self.sceneView.setShowsStatistics_(True)
    
    @objc_method
    def viewWillDisappear_(self, animated: types.c_bool) -> None:
        print('disappear')
        send_super(__class__, self, 'viewDidAppear:', animated)
         
        # Pause the view's AR session.
        self.sceneView.session.pause()
    
    @objc_method
    def renderer_didAddNode_forAnchor_(self, renderer, node, anchor) -> None:
        # Place content only for anchors found by plane detection.
        if not anchor: return 
        planeAnchor = anchor
        
        # Create a custom object to visualize the plane geometry and extent.
        plane = Plane.alloc().initWithAnchor_sceneView_(planeAnchor, self.sceneView)
        
        # Add the visualization to the ARKit-managed node so that it tracks
        # changes in the plane anchor as plane estimation continues.
        node.addChildNode_(plane)
    
    @objc_method
    def renderer_didUpdateNode_forAnchor_(self, renderer, node, anchor) -> None:
        # Update only anchors and nodes set up by `renderer(_:didAdd:for:)`.
        if not anchor: return 
        planeAnchor = anchor
        plane  = node.childNodes.firstObject()
        if not plane: return 
        
        # Update ARSCNPlaneGeometry to the anchor's new estimated shape.
        planeGeometry = plane.meshNode.geometry
        if planeGeometry:
            planeGeometry.updateFromPlaneGeometry_(planeAnchor.geometry)

        # Update extent visualization to the anchor's new bounding rectangle.
        extentGeometry = plane.extentNode.geometry
        if extentGeometry:
            t = repr(planeAnchor)
            x, _, z = (CGFloat(float(i)) for i in t[t.find('extent')+8:-3].split())
            extentGeometry.width = x
            extentGeometry.height = z
            center = tuple(
                float(i) 
                for i in t[t.find('center')+8:].split(')')[0].split()
            )
            plane.extentNode.position = center
        
        # Update the plane's classification and the text position
        if False: return  # ios version > 12.0
        
        return 
        classificationNode = plane.classificationNode,
        classificationGeometry = classificationNode.geometry
        if not classificationGeometry: return 
        
        currentClassification = planeAnchor.classification.description
        oldClassification = classificationGeometry.string
        if oldClassification and oldClassification != currentClassification:
            classificationGeometry.string = currentClassification
            classificationNode.centerAlign()

    @objc_method
    def session_didAddAnchors_(self, session, anchors) -> None:
        frame = session.currentFrame
        if not frame: return 
        
        self.updateSessionInfoLabelForFrame_trackingState_andReason_(frame, frame.camera.trackingState, frame.camera.trackingStateReason)

    @objc_method
    def session_didRemoveAnchors_(self, session, anchors) -> None:
        frame = session.currentFrame
        if not frame: return 
        self.updateSessionInfoLabelForFrame_trackingState_andReason_(frame, frame.camera.trackingState, frame.camera.trackingStateReason)

    @objc_method
    def session_cameraDidChangeTrackingState_(self, session, camera) ->  None:
        self.updateSessionInfoLabelForFrame_trackingState_andReason_(session.currentFrame, camera.trackingState, camera.trackingStateReason)

    @objc_method
    def sessionWasInterrupted_(self, session) ->  None:
        # Inform the user that the session has been interrupted, for example, by presenting an overlay.
        sessionInfoLabel.setText_(ns_from_py("Session was interrupted"))

    @objc_method
    def sessionInterruptionEnded_(self, session) -> None:
        # Reset tracking and/or remove existing anchors if consistent tracking is required.
        sessionInfoLabel.setText_(ns_from_py("Session interruption ended"))
        self.resetTracking()
    
    @objc_method
    def session_didFailWithError_(self, session, error) -> None:
        sessionInfoLabel.setText_(ns_from_py(f"Session failed: {py_from_ns(error.localizedDescription)}"))
        if not error: return 
        
        errorWithInfo = error
        messages = [
            errorWithInfo.localizedDescription,
            errorWithInfo.localizedFailureReason,
            errorWithInfo.localizedRecoverySuggestion
        ]
        
        # Remove optional error messages.
        #errorMessage = messages.compactMap({ $0 }).joined(separator: "\n")
        errorMessage = '\n'.join(py_from_ns(i) for i in messages)
        
        #DispatchQueue.main.async {
        # Present an alert informing about the error that has occurred.
        alertController = UIAlertController.alertControllerWithTitle_message_preferredStyle_(ns_from_py("The AR session failed."), ns_from_py(errorMessage), UIAlertControllerStyleAlert)
        def handler(_: objc_id) -> None:
            alertController.dismissViewControllerAnimated_completion_(True, None)
            self.resetTracking()
        restartAction = UIAlertAction.actionWithTitle_style_handler_(ns_from_py("Restart Session"), UIAlertActionStyleDefault, handler)
        alertController.addAction_(restartAction)
        self.presentViewController_animated_completion(alertController, True, None)
        #}
    
    @objc_method
    def updateSessionInfoLabelForFrame_trackingState_andReason_(self, frame, trackingState, trackingStateReason) -> None:
        # Update the UI to provide feedback on the state of the AR experience.
        message = {
            ARTrackingStateNormal: 
                "Move the device around to detect horizontal and vertical surfaces." if not frame.anchors.count else "",
            ARTrackingStateNotAvailable: 
                "Tracking unavailable.",
            ARTrackingStateLimited:
                {
                    ARTrackingStateReasonInitializing: 
                        "Initializing AR session.",
                    ARTrackingStateReasonRelocalizing:
                        "The AR session is attempting to resume after an interruption.",
                    ARTrackingStateReasonExcessiveMotion:
                        "Tracking limited - Move the device more slowly.",
                    ARTrackingStateReasonInsufficientFeatures:
                        "Tracking limited - Point the device at an area with visible surface detail, or improve lighting conditions."
                }.get(trackingStateReason, '')
        }.get(trackingState, '')
        self.sessionInfoLabel.setText_(ns_from_py(message))
        self.sessionInfoLabel.sizeToFit()
        self.sessionInfoView.setHidden_(not message)

    @objc_method
    def resetTracking(self) -> None:
        configuration = ARWorldTrackingConfiguration.new()
        configuration.planeDetection = \
            ARPlaneDetectionHorizontal | ARPlaneDetectionVertical
        self.sceneView.session.runWithConfiguration_options_(configuration, options=ARSessionRunOptionResetTracking|ARSessionRunOptionRemoveExistingAnchors)

