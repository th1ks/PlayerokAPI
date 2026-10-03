# Карта API Playerok

Документ собран обратной разработкой продакшн-бандла `playerok.com` (Next.js, 233 JS-чанка,
buildId `Pf2Sr9hpZY6M1XSl1Z538`) и эмпирической проверкой маршрутов. Публичного OpenAPI-спека
у площадки нет — проверено 45 типовых путей (`/openapi.json`, `/docs-json`, `/swagger`, …),
везде `404`.

## Бэкенды

| Ключ       | База                                       | Назначение                                             |
|------------|--------------------------------------------|--------------------------------------------------------|
| `public`   | `https://playerok.com/rest-api/public`     | Основной публичный REST, авторизация по cookie `token` |
| `bff`      | `https://bff.playerok.com/rest-api/public` | BFF, авторизация по `Authorization: Bearer <token>`    |
| `auth`     | `https://sapi.playerok.com`                | Сервис авторизации, маршруты `/auth/v1/...`            |
| `internal` | `https://playerok.com/rest-api`            | Служебные и статистические ручки, feature-flags        |
| `admin`    | `https://playerok.com/rest-api/admin`      | Админские ручки                                        |
| `catalog`  | `https://api.playerok.com`                 | Сервис каталога (`items/top`, `items/official`)        |
| `graphql`  | `https://playerok.com/graphql`             | GraphQL: 104 query, 114 mutation, 18 subscription      |
| `ws`       | `wss://ws.playerok.com/graphql`            | GraphQL-подписки (`graphql-transport-ws`)              |

Адрес WebSocket взят из feature-флага `ws-url`:

```http
POST https://playerok.com/rest-api/feature-flags
Content-Type: application/json

{"flagKeys": ["api-url", "ws-url"], "entityContext": {}}
```

Флаг `api-url` на момент разбора выключен (`flagID 10 is not enabled`), то есть переезд
REST на отдельный хост ещё не раскатан. Библиотека умеет читать флаг на старте и, если он
включится, подхватить новый адрес без обновления кода.

## Авторизация

Единственный секрет — cookie `token`, которую выдаёт веб-сессия Playerok.

- `public`, `internal`, `admin`, `graphql`, `ws` — принимают её как cookie `token=<...>`.
- `bff` — принимает тот же токен в заголовке `Authorization: Bearer <...>`.

Получить токен можно либо из браузера (DevTools → Application → Cookies), либо пройдя
e-mail OTP: `POST /auth/send-otp` → `POST /auth/confirm-otp` (при включённой 2FA ещё
`POST /auth/confirm-second-factor`).

## Что закрыто REST, а что — только GraphQL

REST покрывает авторизацию, профиль, файлы, PL-токены, лотереи, Fragment (Telegram Stars),
Steam-депозиты, создание сделки и модерацию товаров. **Каталог, чаты, сообщения, сделки,
отзывы и транзакции по-прежнему живут в GraphQL** — поэтому библиотека гибридная.

### REST-маршруты

Проверка существования: `GET` по каждому пути; `404` — маршрута нет, `401`/`400`/`405`/`200` — есть.

#### `public` и `bff`

| Метод | Путь | Где отвечает |
|---|---|---|
| GET | `/user-geo` | public |
| GET | `/pl-tokens/cashback-config` | public |
| GET | `/pl-tokens/balance` | public |
| GET | `/pl-tokens/history` | public |
| POST | `/pl-tokens/promo-code` | public, bff |
| GET | `/promo-banners` | bff |
| GET | `/quick-deal-widgets` | public |
| GET | `/categories` | public, bff |
| GET | `/top-reviews` | public |
| GET | `/viewer` | bff |
| GET | `/viewer/balance` | bff |
| GET | `/viewer/bindings` | bff |
| GET | `/viewer/chosen-card` | bff |
| GET | `/viewer/config` | bff |
| GET | `/viewer/notifications` | bff |
| GET | `/viewer/two-factor` | bff |
| GET | `/viewer/username-availability` | public, bff |
| POST | `/viewer/registration` | public, bff |
| PUT | `/viewer/avatar` | public, bff |
| POST | `/viewer/two-factor/disable` | public, bff |
| POST | `/viewer/two-factor/enable/request-email-code` | public |
| POST | `/viewer/two-factor/enable/verify-email-code` | public |
| POST | `/viewer/two-factor/enable/confirm` | public |
| GET | `/auth/session-warning` | public |
| POST | `/auth/send-otp` | public, bff |
| POST | `/auth/confirm-otp` | public, bff |
| POST | `/auth/confirm-second-factor` | public, bff |
| POST | `/auth/logout` | public, bff |
| POST | `/deals/create` | public, bff |
| GET | `/deals/{dealId}/supplier-journal` | bff |
| POST | `/item/{id}/discontinue` | public, bff |
| POST | `/item/{id}/republish` | public, bff |
| POST | `/item/{id}/mark-as-checked` | public, bff |
| GET | `/item/{id}/testimonial-stat` | public |
| GET | `/file/v1/upload-url` | public, bff |
| POST | `/file/v1/confirm-upload` | public, bff |
| POST | `/chats/uncensor-message` | public, bff |
| GET | `/chats/uncensor-events/{messageId}` | public |
| GET | `/automation/{itemId}` | public |
| POST | `/automation/validate-attribute` | public, bff |
| POST | `/funds-protection/send-email-code` | public, bff |
| PUT | `/fingerprint/enrich` | public, bff |
| GET | `/user/publish-block-reason` | public |
| GET | `/fragment/config` | public |
| GET | `/fragment/deposits` | public |
| GET | `/fragment/deposits/count` | public |
| GET | `/fragment/deposits/stats` | public |
| GET | `/fragment/deposits/{id}` | public |
| GET | `/fragment/deposits/{id}/logs` | public |
| POST | `/fragment/buy` | public, bff |
| POST | `/fragment/buy-external` | public, bff |
| POST | `/fragment/validate-username` | public, bff |
| GET | `/steam/currency-rate` | public |
| GET | `/steam/check-payment-posibility` | public |
| POST | `/steam/check-promocode` | public, bff |
| POST | `/steam/create-deposit` | public, bff |
| POST | `/steam/create-deposit-external` | public, bff |
| GET | `/lottery/active` | public |
| GET | `/lottery/{lotteryId}/pools` | public |
| GET | `/lottery/{lotteryId}/winners` | public |
| GET | `/lottery/{lotteryId}/telegram-url` | public |
| GET | `/lottery/{lotteryId}/telegram-subscription` | public |
| POST | `/lottery/{lotteryId}/pools/{poolId}/tickets` | public, bff |
| POST | `/lottery/{lotteryId}/daily-claims/claim` | public, bff |
| POST | `/lottery/{lotteryId}/social-claims/claim` | public, bff |
| GET | `/legacy/lottery/{id}` и вложенные | public, bff |
| POST | `/paypal/orders/{orderId}/capture` | public |

#### `auth` (`https://sapi.playerok.com`)

`/auth/v1/viewer`, `/auth/v1/viewer/identities`, `/auth/v1/viewer/two-factor`,
`/auth/v1/viewer/avatar`, `/auth/v1/viewer/two-factor/setup`,
`/auth/v1/users/username-availability`, `/auth/v1/auth/send-otp`,
`/auth/v1/auth/confirm-otp`, `/auth/v1/auth/confirm-second-factor`, `/auth/v1/auth/logout`,
`/auth/v1/files/upload-url`, `/auth/v1/files/{fileId}/confirm`,
`/auth/v1/admin/users/{userId}/...`.

Это следующее поколение авторизации; часть маршрутов ещё не раскатана и отвечает `404`.

#### `internal` и `admin`

`/stats/revenue-stats`, `/items/moderation-logs`, `/items/promo-deals-stats`,
`/items/checker-stats`, `/items/moderator-stats`, `/items/security-stats`,
`/admin/games/fee-multipliers`, `/feature-flags`.

### GraphQL

Схема снята интроспекцией. Корневые типы:

- **Query** — 104 поля, основные: `viewer`, `user`, `users`, `item`, `items`, `chat`, `chats`,
  `chatMessages`, `deal`, `deals`, `games`, `game`, `gameCategories`, `testimonials`,
  `transactions`, `userBalance`.
- **Mutation** — 114 полей, основные: `createChatMessage`, `markChatAsRead`, `updateChat`,
  `createItem`, `updateItem`, `publishItem`, `removeItem`, `increaseItemPriorityStatus`,
  `createDeal`, `updateDeal`, `createTestimonial`, `updateViewerProfile`, `logOut`.
- **Subscription** — 18 полей: `chatMessageCreated`, `chatMessageUpdated`, `chatMessageRemoved`,
  `chatCreated`, `chatUpdated`, `chatMarkedAsRead`, `dealCreated`, `dealUpdated`,
  `itemCreated`, `itemUpdated`, `itemRemoved`, `transactionCreated`, `transactionUpdated`,
  `userBalanceUpdated`, `userUpdated`, `userPhoneVerification`, `steamDepositStatus`,
  `fragmentDepositStatus`.

`Item` и `ItemProfile` — интерфейсы; реализации `MyItem`/`ForeignItem` и
`MyItemProfile`/`ForeignItemProfile`. `UserProfile` — union из `User` и `UserFragment`.

Пагинация курсорная: `Pagination { first, last, before, after }`, сортировка —
`Sort { field, direction }`.
