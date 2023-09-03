def connect_wan():
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect('SSID_NAME', 'Password')
        while not sta_if.isconnected():
            pass
    print('network wan config:', sta_if.ifconfig())


def disconnect_wan():
    import network
    sta_if = network.WLAN(network.STA_IF)
    if sta_if.isconnected():
        print('disconnecting wan network...')
        sta_if.active(False)


def connect_lan():
    import network
    import machine as m

    lan = network.LAN(mdc=m.Pin(23), mdio=m.Pin(18), power=m.Pin(16), id=0, phy_addr=1, phy_type=network.PHY_LAN8720)
    if not lan.isconnected():
        lan.ifconfig(('192.168.5.2', '255.255.255.0', '192.168.5.1', '192.168.5.1'))
        lan.active(True)
    print('network lan config:', lan.ifconfig())


def lan_status():
    import network
    network.AbstractNIC()
    lan = network.LAN(0)
    if lan.isconnected():
        print('network lan config:', lan.ifconfig())
    else:
        print('network disable')


def disconnect_lan():
    import network
    import machine as m

    lan = network.LAN(mdc=m.Pin(23), mdio=m.Pin(18), power=m.Pin(16), id=0, phy_addr=1, phy_type=network.PHY_LAN8720)
    if lan.isconnected():
        print('disconnecting lan network...')
        lan.active(False)


def ls(path=""):
    import os
    print(os.listdir(path))


connect_wan()
# connect_lan()
