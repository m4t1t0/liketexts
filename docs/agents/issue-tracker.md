# Issue tracker: Trello

Issues and specs for this repo live as cards on the **Liketexts** Trello board
(https://trello.com/b/uloZ7GgH), workspace "Rafael Matito's
workspace".

The agent talks to Trello through the **Trello MCP connection**
(the `tools.trello.*` tools in this session). There is no CLI (no Trello
equivalent of `gh`); if the tools are not available in a session, stop and
ask the user to run the operation in Trello rather than guessing.

## Board and lists (state machine)

Board ARI:
`ari:cloud:trello::board/workspace/60af995f36509352c04ab67b/6aa6e4b596a038007182042a`

States are the board lists, in flow order:

| List   | List ARI (…/workspace/<wsId>/<listId>) | Meaning |
| ------ | ------------------------------------- | ------- |
| Backlog | `ari:cloud:trello::list/workspace/60af995f36509352c04ab67b/6aa6e4c5becd98494d84d948` | accepted work not started yet |
| In Progress | `ari:cloud:trello::list/workspace/60af995f36509352c04ab67b/6aa6e4ca2acebf0c32333a77` | being worked in a session (claim by moving) |
| Done | `ari:cloud:trello::list/workspace/60af995f36509352c04ab67b/6aa6e4cd07074d2d9f5a986f` | merged/verified; keep for the record |

A card's state is **the list it is in** — do not use the `complete` flag
(`mark_done`) for state changes; state moves go through card `move`.

## Conventions

- **Create a card**: `trelloWriteCard` with `action: "create"`,
  `listId` = the target list ARI (normally **Backlog**), `name`, `desc`.
  Cards are stateless to name: `Noun phrase + goal`, e.g.
  "Cancel-subscription endpoint route and e2e".
- **Read the board**: `trelloReadCard` with
  `action: "list_by_board"` returns cards grouped by list (one call covers
  the whole board for typical volumes).
- **Read a card**: `trelloReadCard` `action: "get"` with the card ARI. Keep
  the ARI when writing later — the write tools do not accept URLs.
- **Update content**: `trelloWriteCard` `action: "update"` (`name`, `desc`).
- **Change state**: `trelloWriteCard` `action: "move"` with the destination
  list `listId` (and `boardId` when crossing boards).
- **Comment**: `trelloWriteCard` `action: "add_comment"` (`text`). Progress
  notes, decisions, and the closing evidence go in comments.
- **Acceptance criteria**: checklists — `trelloWriteChecklist`
  (`create`, `add_item`) and `trelloReadChecklist` (`list_by_card`).
  The `to-tickets` skill's per-ticket checklists land here.
- There are no labels in use yet; add Trello labels only when a skill needs
  one, via `trelloWriteCard action: "attach_label"`.

## Identifying cards (there are no issue numbers)

Trello cards have no `#123` numbers. Refer to a card by its **short URL**
(`trello.com/c/<shortLink>`, e.g. `https://trello.com/c/YPcmxeCY`), which is
stable and works in commits and docs. Skills that produce `Closes #<n>`
conventions (GitHub-flavoured) do **not** apply here: instead of
auto-closing, the agent **comments on the card** with the commits that
implemented it (hash range) before/at moving it to Done.

## Blocking edges

Trello has no native dependencies. A **blocked** card carries a line at the
top of its description:

> `Blocked by: https://trello.com/c/XXXX, https://trello.com/c/YYYY`

A card is unblocked when every blocker's card is in the **Done** list (or
closed). Keep the line in sync: remove references when blockers land.

## When a skill says "publish to the issue tracker"

Create a card in the **Backlog** list with a fully agent-ready description
(goal, context, scope broken by module, acceptance criteria as a checklist).
For multi-ticket specs, create one card per ticket, each `Blocked by:` only
what it really depends on, and reference the whole picture in the first card.

## When a skill says "fetch the relevant ticket"

Read the card (`trelloReadCard action: "get"`) — description, checklists and
recent comments make up the ticket body.

## Wayfinding / map operations

Not in use (`wayfinder` skill not installed). If it is ever enabled, model
the map as a card whose checklist enumerates child cards.
