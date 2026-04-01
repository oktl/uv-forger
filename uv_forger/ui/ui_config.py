"""UI configuration constants.

This module centralizes all UI styling constants including dimensions,
colors, spacing, and provider configurations to ensure consistency
across the application.
"""

import flet as ft


class UIConfig:
    """Centralized UI styling and sizing constants.

    All magic numbers for UI dimensions, spacing, colors, and styling
    are defined here for easy modification and consistency.
    """

    # Progress Ring / Bar
    PROGRESS_RING_SIZE = 18
    PROGRESS_RING_STROKE_WIDTH = 2
    PROGRESS_BAR_WIDTH = 300

    # Icon Sizes
    ICON_SIZE_DEFAULT = 18

    # Border Radius
    BORDER_RADIUS_DEFAULT = 8

    # Border Widths
    BORDER_WIDTH_THIN = 1
    BORDER_WIDTH_DEFAULT = 2

    # Spacing
    SPACING_SMALL = 10
    SPACING_LARGE = 20
    SPACING_XLARGE = 80

    # Padding
    PADDING_SECTION = 15

    # Text Sizes
    TEXT_SIZE_SMALL = 12

    # Vertical Spacing (Container heights for spacing)
    VSPACE_SMALL = 10

    # Dialog Dimensions
    DIALOG_WIDTH = 700
    DIALOG_HEIGHT = 800
    DIALOG_CONTENT_PADDING = 20
    DIALOG_TITLE_SIZE = 20

    # Components Layout
    MAIN_TITLE_SIZE = 24
    SECTION_TITLE_SIZE = 16
    APPBAR_TITLE_SIZE = 14
    APPBAR_TOOLBAR_HEIGHT = 30
    SECTION_WIDTH = 780  # Project Structure section (right column)
    LEFT_SECTION_WIDTH = 660  # Path and Options sections (left column)
    SPLIT_CONTAINER_WIDTH = (
        350  # fits two containers + gap within SECTION_WIDTH border/padding
    )
    SUBFOLDERS_HEIGHT = 410
    STRUCTURE_DIVIDER_HEIGHT = 575  # vertical divider between folder/package columns
    BUTTON_WIDTH_BUILD = 300
    BUTTON_WIDTH_ACTION = 110  # Reset and Exit buttons
    BUTTON_WIDTH_STRUCTURE = (
        170  # folder/package split-panel buttons (two per row in 350px container)
    )

    # Folder Tree Display
    FOLDER_TREE_INDENT_PX = 14  # pixels per indent level
    FOLDER_ITEM_PADDING = ft.Padding(left=4, right=4, top=1, bottom=1)
    SELECTED_ITEM_BGCOLOR = ft.Colors.BLUE_800
    SELECTED_ITEM_BORDER_COLOR = ft.Colors.BLUE_400

    # Semantic Status Colors (theme-invariant)
    COLOR_SUCCESS = ft.Colors.GREEN_600
    COLOR_ERROR = ft.Colors.RED_600
    COLOR_WARNING = ft.Colors.ORANGE_600
    COLOR_INFO = ft.Colors.BLUE_600

    # Semantic UI Colors (theme-invariant)
    COLOR_CHECKBOX_ACTIVE = ft.Colors.GREEN  # checkbox label when checked
    COLOR_VALIDATION_OK = ft.Colors.GREEN  # text field valid icon
    COLOR_VALIDATION_ERROR = ft.Colors.RED  # text field invalid icon
    COLOR_FOLDER_ICON = ft.Colors.AMBER_400  # folder icon in tree
    COLOR_FILE_ICON = ft.Colors.GREY_500  # file icon in tree
    COLOR_FILE_TEXT = ft.Colors.GREY_400  # file name text in tree

    # Button Background Colors (full-saturation for visual weight)
    COLOR_BTN_BUILD = ft.Colors.GREEN
    COLOR_BTN_RESET = ft.Colors.ORANGE
    COLOR_BTN_EXIT = ft.Colors.RED
