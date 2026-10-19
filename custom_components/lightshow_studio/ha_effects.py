"""Slow, capability-independent show frames for ordinary Home Assistant lights.

Frames use standard light actions, never Zigbee2MQTT effect names. HA translates
RGB to a light's RGBW/RGBWW/HS/XY mode. Hardware effects remain a separate route.
"""
import colorsys
import math


def frame(cue: dict, elapsed: float, seed: int = 0) -> dict:
    """Return one static cue; speed determines the period, not the request rate."""
    result = dict(cue)
    mode = cue['mode']
    phase = elapsed / (12 + (100 - cue['speed']) * .6)
    wave = (1 + math.sin(phase * math.tau)) / 2
    level = 1.0
    rgb = (255, 145, 60)
    if mode in ('candle', 'fireplace', 'sparkle', 'glisten'):
        # Deterministic per fixture: independent flicker without a shared RNG.
        pulse = (math.sin(elapsed * 1.7 + seed) + math.sin(elapsed * 2.3 + seed * .7) + 2) / 4
        level = .45 + .55 * pulse
        rgb = (255, round(70 + 95 * pulse), 25) if mode in ('candle', 'fireplace') else (255, 230, 185)
    elif mode == 'blink':
        result['mode'] = 'white' if int(elapsed / max(2, 8 - cue['speed'] * .06)) % 2 == 0 else 'off'
        return result
    elif mode == 'breathe':
        level = .15 + .85 * wave
    elif mode in ('sunset', 'sunrise'):
        progress = min(1, elapsed / (30 + (100 - cue['speed']) * 3))
        if mode == 'sunset':
            progress = 1 - progress
        level = .08 + .92 * progress
        rgb = (255, round(45 + 165 * progress), round(10 + 110 * progress))
    else:
        palettes = {'underwater': (.47, .64), 'cosmos': (.65, .9),
                    'sunbeam': (.05, .15), 'enchant': (.72, 1.05), 'opal': (.0, 1.0)}
        low, high = palettes.get(mode, (0, 1))
        hue = (phase % 1) if mode == 'colorloop' else low + (high - low) * wave
        rgb = tuple(round(v * 255) for v in colorsys.hsv_to_rgb(hue % 1, .8, 1))
    result.update(mode='custom_color', color='#%02X%02X%02X' % rgb,
                  brightness=max(1, round(cue['brightness'] * level)),
                  kelvin=2700 if mode in ('candle', 'fireplace', 'sunset', 'sunrise', 'breathe') else 4000)
    return result
