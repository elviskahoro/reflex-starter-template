

<!-- entire-agent:begin -->
Read .entire/agent-guide.md for this repository's workflow, source inspection, and verification guidance.
@.entire/agent-guide.md
<!-- entire-agent:end -->

## RWX PR previews

`.rwx/preview.yml` defines the preview app (see the `rwx-reflex-preview` skill in
`.agents/skills/`). Validate with `rwx lint .rwx/preview.yml`; test with
`rwx run .rwx/preview.yml --init pull-request-number=0 --wait`. Previews are
private: access them with the `X-RWX-Access-Token` header (RWX docs). Only use
behavior documented in the RWX docs or `rwx --help`. Known open issue: the
frontend's baked-in `localhost:8000` API URL is patched in the build step
(undocumented workaround, WebSocket events unverified).
