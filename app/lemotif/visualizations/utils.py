"""
utils.py
Visualization helpers.
"""

import cv2
import numpy as np
import random
from PIL import ImageFont, ImageDraw, Image


def rgb_to_hsv(rgb):
    """Convert RGB color to HSV."""
    r, g, b = rgb
    r = float(r)
    g = float(g)
    b = float(b)
    high = max(r, g, b)
    low = min(r, g, b)
    h, s, v = high, high, high

    d = high - low
    s = 0 if high == 0 else d/high

    if high == low:
        h = 0.0
    else:
        h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        h /= 6

    return h*360, s*100, v


def fill_color(shape, color, border_color=None, color_type='rgb'):
    """Fill in shape delineated by black lines with specified color."""
    # Get coordinates of borders
    borders = np.array(np.where(shape == 0)).T
    filled = np.ones((shape.shape[0], shape.shape[1], 3), dtype='uint8')*255
    if color_type == 'rgb':
        # Switch to BGR format if RGB
        color = [color[2], color[1], color[0]]
    # Flood fill interior region
    center = np.int32(np.mean(borders[:, [1, 0]], axis=0))
    dist = borders - center
    mean_dist = np.mean(dist, axis=0)
    poly_center = np.int32(center - mean_dist)
    filled[..., 0] = shape
    filled = cv2.floodFill(filled, None, (poly_center[0], poly_center[1]), color)[1]
    if border_color is None:
        filled[shape != 255] = [255, 255, 255]
    else:
        filled[shape != 255] = list(np.array(color)*border_color)
    return filled


def bg_mask(icon_resized, colors, border_color):
    """Mask region."""
    mask = np.zeros(icon_resized.shape[:-1], dtype=bool)
    for color in colors:
        mask = np.logical_or(mask,
                             np.all(icon_resized == [color['rgb'][2], color['rgb'][1], color['rgb'][0]], -1))
    if border_color:
        mask = np.logical_or(mask, np.all(icon_resized != [255, 255, 255], -1))

    return mask


def overlap_mask(canvas, icon_resized, adj_y, icon_size, start, background):
    """Return masks based on overlap of existing placements and new placement."""
    # Blend region = non-background regions in canvas and icon
    mask = np.logical_and(
        np.all(canvas[adj_y:adj_y + icon_size, start[1]:start[1] + icon_size] != background, -1),
        np.all(icon_resized != background, -1))
    # Regions where canvas = background and icon is not background are overridden by icon
    new_mask = np.all(canvas[adj_y:adj_y + icon_size, start[1]:start[1] + icon_size] == background, -1)

    return mask, new_mask


def fill_canvas(canvas, background, mask, size, icon_resized, start, adj_y, icon_size, alpha):
    """Fill canvas based on mask."""
    if mask is None:
        # If canvas is not blank, alpha-blend only overlap regions
        if np.sum(canvas) != np.sum(background) * size[0] * size[1]:
            mask, new_mask = overlap_mask(canvas, icon_resized, adj_y, icon_size, start, background)
            canvas[adj_y:adj_y + icon_size, start[1]:start[1] + icon_size][new_mask] = icon_resized[new_mask]
        else:
            mask = np.ones(icon_resized.shape[:-1], dtype=bool)
    # Blend in mask region only
    canvas[adj_y:adj_y + icon_size, start[1]:start[1] + icon_size][mask] = \
        canvas[adj_y:adj_y + icon_size, start[1]:start[1] + icon_size][mask] * alpha + icon_resized[mask] * (1 - alpha)

    return canvas


def shape_bool_mask(icons, topics, size, border_color):
    """Boolean mask based on shape."""
    outline_mask = fill_color(cv2.resize(icons[random.choice(topics)], size), (0, 0, 0), border_color) / 255
    outline_mask = ~outline_mask.astype(bool)
    return outline_mask


def apply_shape(canvas, icons, topics, size, border_color, background):
    """Apply shape to canvas, retaining only region within shape."""
    outline_mask = shape_bool_mask(icons, topics, size, border_color)
    final_canvas = np.ones((size[0], size[1], 3))
    final_canvas[..., :] = background
    final_canvas[outline_mask] = canvas[outline_mask]
    return final_canvas


def add_labels(canvas, topics, emotions, colors, font_path='/System/Library/Fonts/HelveticaNeue.ttc'):
    """Add text labels to bottom of image."""
    label_canvas = np.ones((20, canvas.shape[1], 3))*255
    label_canvas = Image.fromarray(label_canvas.astype('uint8'))
    draw = ImageDraw.Draw(label_canvas)
    font = ImageFont.truetype(font_path, 14)

    for topic in topics:
        if topic is not None:
            draw.text((10, 0), '#' + topic, font=font, fill=(0, 0, 0))
            x_offset = font.getsize('#' + topic)[0] + 15
        else:
            x_offset = 10

    for emotion in emotions:
        draw.text((x_offset, 0), '#' + emotion, font=font, fill=colors[emotion]['rgb'][::-1])
        x_offset += font.getsize('#' + emotion)[0] + 10

    canvas = np.concatenate((canvas, label_canvas), axis=0)

    return canvas