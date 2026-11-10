// 3D companion view: the active companion is a glowing core; the others orbit it.
// state: "idle" | "listening" | "thinking" | "speaking"
import QtQuick
import QtQuick3D

Item {
    id: root
    anchors.fill: parent
    property color coreColor: bridge ? bridge.color : "#4FC3F7"
    property string mood: bridge ? bridge.mood : "idle"
    property string label: bridge ? bridge.name : "JARVIS"
    property var others: bridge ? bridge.others : []
    property real level: bridge ? bridge.level : 0.0   // voice level 0..1 while speaking

    Rectangle { anchors.fill: parent; color: "#0B0F17" }

    View3D {
        id: view
        anchors.fill: parent
        environment: SceneEnvironment {
            clearColor: "#0B0F17"
            backgroundMode: SceneEnvironment.Color
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.Medium
        }

        PerspectiveCamera { id: cam; position: Qt.vector3d(0, 40, 320); eulerRotation.x: -7 }
        DirectionalLight { eulerRotation.x: -35; eulerRotation.y: -30; brightness: 1.2 }
        PointLight { position: Qt.vector3d(0, 0, 0); color: root.coreColor; brightness: 3; quadraticFade: 0.0004 }

        Node {
            id: scene
            NumberAnimation on eulerRotation.y {
                from: 0; to: 360; loops: Animation.Infinite
                duration: root.mood === "thinking" ? 4000 : 22000
            }

            // core
            Model {
                id: core
                source: "#Sphere"
                property real pulse: 1.0
                scale: Qt.vector3d(0.9 * pulse, 0.9 * pulse, 0.9 * pulse)
                materials: PrincipledMaterial {
                    baseColor: root.coreColor
                    emissiveFactor: Qt.vector3d(root.coreColor.r * 0.8, root.coreColor.g * 0.8, root.coreColor.b * 0.8)
                    metalness: 0.2; roughness: 0.25
                }
                SequentialAnimation on pulse {
                    loops: Animation.Infinite
                    running: root.mood !== "speaking"
                    NumberAnimation { to: root.mood === "listening" ? 1.18 : 1.06; duration: root.mood === "listening" ? 350 : 1600; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 1.0; duration: root.mood === "listening" ? 350 : 1600; easing.type: Easing.InOutSine }
                }
                Binding { target: core; property: "pulse"; value: 1.0 + root.level * 0.35; when: root.mood === "speaking" }
            }

            // halo ring made of small beads
            Repeater3D {
                model: 36
                Model {
                    source: "#Sphere"
                    property real a: index / 36 * Math.PI * 2
                    position: Qt.vector3d(Math.cos(a) * 95, Math.sin(a * 3) * 4, Math.sin(a) * 95)
                    scale: Qt.vector3d(0.05, 0.05, 0.05)
                    materials: PrincipledMaterial { baseColor: root.coreColor; emissiveFactor: Qt.vector3d(0.6, 0.6, 0.6); lighting: PrincipledMaterial.NoLighting }
                }
            }

            // orbiting companions
            Repeater3D {
                model: root.others
                Node {
                    property real a: index / Math.max(1, root.others.length) * 360
                    eulerRotation.y: a
                    eulerRotation.z: 12
                    Model {
                        source: "#Sphere"
                        position: Qt.vector3d(150, 0, 0)
                        scale: Qt.vector3d(0.22, 0.22, 0.22)
                        materials: PrincipledMaterial { baseColor: modelData; roughness: 0.4; emissiveFactor: Qt.vector3d(0.25, 0.25, 0.25) }
                    }
                }
            }
        }
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom; anchors.bottomMargin: 18
        spacing: 4
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.label; color: root.coreColor; font.pixelSize: 22; font.bold: true; font.letterSpacing: 4 }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.mood.toUpperCase(); color: "#8899AA"; font.pixelSize: 12; font.letterSpacing: 3 }
    }
}
