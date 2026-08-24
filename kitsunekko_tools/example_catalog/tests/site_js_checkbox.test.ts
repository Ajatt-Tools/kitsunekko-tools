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

    test.each([
        {
            name: "selects an inclusive range on Shift-click",
            actions: [
                { index: 0, shiftKey: false },
                { index: 3, shiftKey: true },
            ],
            expectedChecked: [true, true, true, true],
            expectedCount: "4",
        },
        {
            name: "selects an inclusive range in reverse document order",
            actions: [
                { index: 3, shiftKey: false },
                { index: 0, shiftKey: true },
            ],
            expectedChecked: [true, true, true, true],
            expectedCount: "4",
        },
        {
            name: "applies the current checkbox state when Shift-clicking to deselect a range",
            actions: [
                { index: 0, shiftKey: false },
                { index: 3, shiftKey: true },
                { index: 1, shiftKey: false },
                { index: 3, shiftKey: true },
            ],
            expectedChecked: [true, false, false, false],
            expectedCount: "1",
        },
    ])("$name", ({ actions, expectedChecked, expectedCount }) => {
        const { win, sections } = bootSite();
        const section = sections[0];
        const files = checkboxes(section);

        for (const { index, shiftKey } of actions) {
            clickCheckbox(win, files[index], shiftKey);
        }

        expect(files.map(file => file.checked)).toEqual(expectedChecked);
        expect(selectedCount(section)).toBe(expectedCount);
    });

    test.each([
        { anchorSectionIndex: 0, otherSectionIndex: 1 },
        { anchorSectionIndex: 1, otherSectionIndex: 0 },
    ])(
        "keeps Shift-click anchors inside subtitle section $anchorSectionIndex",
        ({ anchorSectionIndex, otherSectionIndex }) => {
            const { win, sections } = bootSite({
                sections: [
                    { type: "ass", count: 3 },
                    { type: "srt", count: 3 },
                ],
            });
            const anchorFiles = checkboxes(sections[anchorSectionIndex]);
            const otherFiles = checkboxes(sections[otherSectionIndex]);

            clickCheckbox(win, anchorFiles[0]);
            clickCheckbox(win, otherFiles[1]);
            clickCheckbox(win, anchorFiles[2], true);

            expect(anchorFiles.map(file => file.checked)).toEqual([true, true, true]);
            expect(otherFiles.map(file => file.checked)).toEqual([false, true, false]);
            expect(selectedCount(sections[anchorSectionIndex])).toBe("3");
            expect(selectedCount(sections[otherSectionIndex])).toBe("1");
        },
    );
});
