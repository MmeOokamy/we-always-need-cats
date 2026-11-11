// KWin script loaded by cats.py.
// Under Wayland an application cannot know the mouse position: KWin does, and
// forwards it from here to the program over D-Bus.

var last = "";

function report() {
    var p = workspace.cursorPos;
    var t = workspace.virtualScreenSize;
    var message = Math.round(p.x) + "," + Math.round(p.y) + "," + t.width + "," + t.height;
    try {
        // Usable area (task bar excluded) of the active screen: where cats sit.
        var a = workspace.clientArea(KWin.MaximizeArea, workspace.activeScreen, workspace.currentDesktop);
        message += "," + a.x + "," + a.y + "," + a.width + "," + a.height;
    } catch (e) {}
    if (message !== last) {
        last = message;
        callDBus("org.weneedcats", "/Cursor", "org.weneedcats.Cursor", "Position", message);
    }
}

try {
    var timer = new QTimer();
    timer.interval = 50;
    timer.timeout.connect(report);
    timer.start();
} catch (e) {
    workspace.cursorPosChanged.connect(report);
}
report();
