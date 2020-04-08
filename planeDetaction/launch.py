try:
    from app.viewcontroller import MyViewController
except RuntimeError:
    import os
    os._exit(0)
from rubicon.objc import CGRect,ObjCInstance
import objc_util
import ui


class MainView(ui.View):
    def __init__(self):
        vc = MyViewController.alloc().init()
        self.arvc = vc
        ObjCInstance(self.objc_instance).addSubview_(vc.view)
        
    def present(self, *args, **kwargs):
        super().present(*args, **kwargs)
        ObjCInstance(self.objc_instance).nextResponder.addChildViewController_(self.arvc)
    
    def layout(self):
        frame = CGRect((0,0),self.frame.size.as_tuple())
        self.arvc.view.setFrame_(frame)
        self.arvc.sceneView.setFrame_(frame)

@objc_util.on_main_thread
def main():
    global vc, main_v
    main_v = MainView()
    main_v.present()
    

if __name__ == '__main__':
    main()

