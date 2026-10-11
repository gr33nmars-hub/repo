# Product

<!-- impeccable:product-schema 1 -->

## Platform

Windows desktop application (Tauri), developed with Vite

## Users

Players using an educational, local desktop casino to explore its game tables with virtual demo chips. The brief does not identify a narrower demographic.

## Product Purpose

NOIR Casino Club presents blackjack, roulette, and slots in a desktop interface backed by a local Python/FastAPI service. Success means the player can see their real demo-chip balance and reach a table or their history without confusion.

## Positioning

Game outcomes and the demo-chip balance come from the local backend; the interface does not supply or simulate results.

## Operating Context

The product runs as a Windows desktop application using a Tauri shell and is also developed through Vite. Players move between the lobby, game tables, and their round history.

## Capabilities and Constraints

- Supported rooms are lobby, blackjack, slots, roulette, and history.
- The UI reads balance and player statistics from the backend API.
- Chips are virtual and for educational/demo play only. There are no real-money operations, payments, deposits, withdrawals, or external financial integrations.
- The existing React + TypeScript + Vite frontend, Tauri shell, and Python/FastAPI backend remain in place.

## Brand Commitments

The product name is NOIR Casino Club. The requested product world is a stylish night club with casino tables; its owner/dealer is an adult, stylized character with a tasteful cabaret influence.

## Evidence on Hand

Balance, history, and player statistics come from the local API. The slots table computes a theoretical return from its configured reel strips and paytable; this is not an observed result or an independent fairness audit. The interface has no real-money data, live-player count, or external endorsements to display.

## Product Principles

- Show real game and account state from the backend.
- Make the available tables and current room easy to understand.
- Keep all play within virtual demo chips.
- Preserve access to existing game rooms and history.

## Accessibility & Inclusion

The desktop interface must support keyboard navigation, visible focus, readable contrast, reduced motion preferences, and the 920×640 minimum application window.
