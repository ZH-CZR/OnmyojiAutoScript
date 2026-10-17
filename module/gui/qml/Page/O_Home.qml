import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Controls
import FluentUI

import "../Component"


SplitPanel{

    property string configName: ""

    onTitleChanged: {
        if(title === "Home"){
//            const comp = Qt.createComponent("../../qml/Page/Home.qml")
//            if (comp.status === Component.Ready) {
//                setLoader(comp)

//            }
            showDefalut()
        }else if(title === "NotifyTest"){
            const notify_test = Qt.createComponent("../../qml/Content/NotifyTest.qml")
            if (notify_test.status === Component.Ready) {
                setLoader(notify_test)
            }
        }
    }
    Component.onCompleted:{
        var data = { "Home":[], 'NotifyTest':[]}
        create(data)

        var comp = Qt.createComponent("../../qml/Page/Home.qml")
        if (comp.status === Component.Ready) {
            setDefalut(comp)
        }
    }
}

