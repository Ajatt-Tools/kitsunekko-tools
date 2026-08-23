// Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { describe, expect, test } from "vitest";

import { bootSite, checkboxes, clickCheckbox, downloadButton, selectedCount } from "./site_js_helpers";

describe("subtitle checkbox selection", () => {
    test("updates the selected count and download button on normal checkbox changes", () => {
        const { win, sections } = bootSite();
        const section = sections[0];
        const files = checkboxes(section);

        clickCheckbox(win, files[0]);

        expect(selectedCount(section)).toBe("1");
        expect(downloadButton(section).disabled).toBe(false);
    });

    test("updates the selected count on keyboard-style checkbox changes", () => {
        const { win, sections } = bootSite();
        const section = sections[0];
        const files = checkboxes(section);

        files[0].checked = true;
        files[0].dispatchEvent(new win.Event("change", { bubbles: true }));

        expect(selectedCount(section)).toBe("1");
        expect(downloadButton(section).disabled).toBe(false);
    });

    test("selects an inclusive range on Shift-click", () => {
        const { win, sections } = bootSite();
        const section = sections[0];
        const files = checkboxes(section);

        clickCheckbox(win, files[0]);
        clickCheckbox(win, files[3], true);

        expect(files.map(file => file.checked)).toEqual([true, true, true, true]);
        expect(selectedCount(section)).toBe("4");
    });

    test("applies the current checkbox state when Shift-clicking to deselect a range", () => {
        const { win, sections } = bootSite();
        const section = sections[0];
        const files = checkboxes(section);

        clickCheckbox(win, files[0]);
        clickCheckbox(win, files[3], true);
        clickCheckbox(win, files[1]);
        clickCheckbox(win, files[3], true);

        expect(files.map(file => file.checked)).toEqual([true, false, false, false]);
        expect(selectedCount(section)).toBe("1");
    });

    test("keeps Shift-click ranges inside the current subtitle format section", () => {
        const { win, sections } = bootSite({
            sections: [
                { type: "ass", count: 3 },
                { type: "srt", count: 3 },
            ],
        });
        const assFiles = checkboxes(sections[0]);
        const srtFiles = checkboxes(sections[1]);

        clickCheckbox(win, assFiles[0]);
        clickCheckbox(win, srtFiles[2], true);

        expect(assFiles.map(file => file.checked)).toEqual([true, false, false]);
        expect(srtFiles.map(file => file.checked)).toEqual([false, false, true]);
        expect(selectedCount(sections[0])).toBe("1");
        expect(selectedCount(sections[1])).toBe("1");
    });
});
