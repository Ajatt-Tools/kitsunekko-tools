// Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";

const dirname = path.dirname(fileURLToPath(import.meta.url));
const siteScriptPath = path.join(dirname, "..", "resources", "site.js");
const siteScript = fs.readFileSync(siteScriptPath, "utf8");

type SectionOptions = {
    type: string;
    count: number;
};

type BootSiteOptions = {
    sections?: SectionOptions[];
};

function checkboxRow(sectionType: string, index: number): string {
    return `
    <tr data-timestamp="${index}" data-file-size="${index}">
      <td data-cell="#" class="entry_number"><span class="font-mono">${index}</span></td>
      <td data-cell="Name" class="entry_name">
        <input type="checkbox" class="file-checkbox" data-download-url="/subtitles/${sectionType}/${index}.srt" data-filename="${sectionType}-${index}.srt">
        <a href="/subtitles/${sectionType}/${index}.srt" download="${sectionType}-${index}.srt">${sectionType}-${index}.srt</a>
      </td>
      <td data-cell="Size" class="file_size"><span class="font-mono">${index} B</span></td>
      <td data-cell="Last modified" class="last_modified"><span class="font-mono">01 Jan 2026 00:00:00</span></td>
    </tr>`;
}

function subtitleSection({ type, count }: SectionOptions): string {
    return `
    <section class="group_${type}" data-entry-name="Example ${type}">
      <div class="button_row_container download_bar">
        <button type="button" class="select-all-btn">Select all</button>
        <button type="button" class="download-selected-btn" disabled>Download selected (<span class="selected-count">0</span>)</button>
      </div>
      <table class="entries_table file_list_table">
        <thead>
          <tr>
            <th scope="col" class="entry_number">#</th>
            <th scope="col" class="entry_name">Name</th>
            <th scope="col" class="file_size">Size</th>
            <th scope="col" class="last_modified">Last modified (UTC)</th>
          </tr>
        </thead>
        <tbody>${Array.from({ length: count }, (_, index) => checkboxRow(type, index + 1)).join("")}</tbody>
      </table>
    </section>`;
}

function makeSiteDom({ sections = [{ type: "srt", count: 4 }] }: BootSiteOptions = {}): JSDOM {
    return new JSDOM(`<main class="no-js">${sections.map(subtitleSection).join("")}</main>`, {
        runScripts: "outside-only",
        url: "https://subtitles.example.test/anime_tv/example.html",
    });
}

function loadSiteScript(win: Window): void {
    win.eval(`${siteScript}\n//# sourceURL=file://${siteScriptPath}`);
    win.document.dispatchEvent(new win.Event("DOMContentLoaded"));
}

export function bootSite(options: BootSiteOptions = {}): { dom: JSDOM; win: Window; sections: HTMLElement[] } {
    const dom = makeSiteDom(options);
    const win = dom.window;
    win.URL.createObjectURL = () => "blob:subtitles-test";
    win.URL.revokeObjectURL = () => {};
    loadSiteScript(win);
    return {
        dom,
        win,
        sections: [...win.document.querySelectorAll("section[data-entry-name]")] as HTMLElement[],
    };
}

export function checkboxes(section: HTMLElement): HTMLInputElement[] {
    return [...section.querySelectorAll(".file-checkbox")] as HTMLInputElement[];
}

export function clickCheckbox(win: Window, checkbox: HTMLInputElement, shiftKey = false): void {
    checkbox.dispatchEvent(new win.MouseEvent("click", { bubbles: true, shiftKey }));
}

export function selectedCount(section: HTMLElement): string {
    return section.querySelector(".selected-count")?.textContent ?? "";
}

export function downloadButton(section: HTMLElement): HTMLButtonElement {
    const win = section.ownerDocument.defaultView;
    const button = section.querySelector(".download-selected-btn");
    if (!win || !(button instanceof win.HTMLButtonElement)) {
        throw new Error("download button not found");
    }
    return button;
}
