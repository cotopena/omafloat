# Third-party notices

OmaPeek's own contributions are licensed under the MIT license in [LICENSE](LICENSE),
Copyright (c) 2026 Gus. The upstream notice below applies to the Omarchy code
adapted in this package and must accompany copies or substantial portions of it.

## Omarchy dropdown

`OmaPeekDropdown.qml` is adapted from Omarchy's `shell/Ui/Dropdown.qml`.
It retains the themed trigger, popup, option rendering, and keyboard navigation,
with OmaPeek changes for accessibility, disabled-state handling, bound component
scope, and selection readback.

Provenance checked on 2026-10-05:

- Official repository: [omacom/omarchy](https://github.com/omacom/omarchy), default branch `quattro`.
- Reference revision: `b9e0ac4f1d8b33ab01af0cbb3a95c8667ee69eb3` (the branch head at verification time; not a claim about the original adaptation date).
- [Upstream dropdown](https://github.com/omacom/omarchy/blob/b9e0ac4f1d8b33ab01af0cbb3a95c8667ee69eb3/shell/Ui/Dropdown.qml).
- [Upstream license](https://github.com/omacom/omarchy/blob/b9e0ac4f1d8b33ab01af0cbb3a95c8667ee69eb3/LICENSE).
- Read-only installed reference: `/usr/share/omarchy/shell/Ui/Dropdown.qml`,
  byte-for-byte identical to the upstream dropdown at that revision.
- Dropdown SHA-256: `6e2b847a33f5dedb96f65757d284f40b90073b3b34fd31abb84b2d471814fc5c`.

The installed `/usr/share/omarchy` tree does not contain a `LICENSE` file;
the exact notice below was retrieved from the official repository at the same
revision. No separate notice appears in the upstream dropdown file.

### Omarchy MIT license notice (verbatim)

```text
Copyright (c) David Heinemeier Hansson

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## Runtime components and package assets

OmaPeek uses installed Omarchy `qs.Ui` and `qs.Commons` modules. In particular,
`OmaPeekButton.qml`, `OmaPeekToggle.qml`, `OmaPeekPanel.qml`, and
`OmaPeekWidget.qml` extend or use Omarchy UI components; those imported modules
are supplied by Omarchy rather than bundled here. The notice above records the
Omarchy attribution for the dropdown adaptation shipped in this package.

The attribution review compared the package's QML and helper scripts with the
installed Omarchy sources. It found no other substantial copied component.
Short shared QML layout/import patterns do not establish additional provenance.
`OPeekIcon.qml` defines its geometry directly in QML; no external icon file or
font is bundled. The package screenshot is a rendered preview of the plugin,
including its Omarchy-themed UI. This review does not establish the provenance
of every transitive runtime dependency; their notices remain with their own
distributions.
