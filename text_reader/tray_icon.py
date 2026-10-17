import pystray
from PIL import Image, ImageDraw

RATE_PRESETS = [
    ("0.75x", -3),
    ("1x (Normal)", 0),
    ("1.25x", 3),
    ("1.5x", 5),
    ("2x", 8),
]


def make_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, size - 2, size - 2), fill=(30, 144, 255, 255))
    d.rectangle((18, 30, 25, 46), fill=(255, 255, 255, 255))
    d.rectangle((29, 20, 36, 46), fill=(255, 255, 255, 255))
    d.rectangle((40, 26, 47, 46), fill=(255, 255, 255, 255))
    return img


def build_icon(app):
    def voice_item(description, voice_id):
        def action(icon, item):
            app.set_voice(voice_id)

        def checked(item):
            return app.config.voice_id == voice_id

        return pystray.MenuItem(description, action, checked=checked, radio=True)

    def rate_item(label, rate):
        def action(icon, item):
            app.set_rate(rate)

        def checked(item):
            return app.config.rate == rate

        return pystray.MenuItem(label, action, checked=checked, radio=True)

    voice_menu = pystray.Menu(*[voice_item(desc, vid) for desc, vid in app.voices])
    rate_menu = pystray.Menu(*[rate_item(label, rate) for label, rate in RATE_PRESETS])

    menu = pystray.Menu(
        pystray.MenuItem("Show Window", lambda icon, item: app.show_window(), default=True),
        pystray.MenuItem(
            lambda item: f"Read Selection   ({app.config.hotkey_read})", lambda icon, item: app.read_selection_async()
        ),
        pystray.MenuItem("Pause / Resume", lambda icon, item: app.toggle_pause()),
        pystray.MenuItem(lambda item: f"Stop   ({app.config.hotkey_stop})", lambda icon, item: app.stop()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Voice", voice_menu),
        pystray.MenuItem("Speed", rate_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", lambda icon, item: app.request_shutdown()),
    )
    return pystray.Icon("text_reader", make_image(), "Text Reader", menu)
