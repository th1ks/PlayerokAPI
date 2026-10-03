# PlayerokAPI

Асинхронная библиотека для API маркетплейса Playerok. Пакет-папка `PlayerokAPI/`
по образцу `FunPayAPI` из FunPayCardinal.

## Git

- Коммиты только от имени пользователя: `th1ks <stepand2010@gmail.com>`.
- **Не добавлять `Co-Authored-By`** и любые другие подписи ассистента —
  ни в коммиты, ни в описания пулл-реквестов.
- Сообщение коммита короткое: одна строка. Тело только если без него непонятно,
  и тогда — пара строк, не простыня.
- Ветки: `main` — релизы, `develop` — интеграционная, фичи — `feat/*`, правки — `fix/*`.
  Пулл-реквесты идут в `develop`.

## Файлы

Не плодить бюрократию: никаких `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
`CHANGELOG.md`, шаблонов issue и PR, развесистых `docs/`. Только то, что реально нужно:
код, `README.md`, `LICENSE`, `pyproject.toml`, CI.

## Код

- Python 3.10+, весь публичный код типизирован.
- Зависимости только `httpx` и `websockets` — библиотека лёгкая, новые пакеты
  добавляются с обоснованием.
- Только асинхронный ввод-вывод, синхронных HTTP-вызовов нет.
- Комментарии по делу и короткие. Не пересказывать код словами.

## Архитектура

REST-first гибрид. Где у площадки есть REST — идём в REST, остальное через GraphQL.
Админские и внутренние ручки не реализуем — только то, что нужно обычному клиенту.

| Транспорт | Адрес                                      | Что закрывает                                        |
|-----------|--------------------------------------------|------------------------------------------------------|
| REST      | `https://playerok.com/rest-api/public`     | основной публичный, cookie `token`                   |
| REST      | `https://bff.playerok.com/rest-api/public` | BFF, `Authorization: Bearer <token>`                 |
| REST      | `https://sapi.playerok.com`                | авторизация, `/auth/v1/...`                          |
| GraphQL   | `https://playerok.com/graphql`             | товары, чаты, сделки, отзывы, транзакции             |
| WS        | `wss://ws.playerok.com/graphql`            | подписки, подпротокол `graphql-transport-ws`         |

Авторизация — одна cookie `token`. Тот же токен уходит в BFF как Bearer.
Адрес WebSocket берётся из feature-флага `ws-url`
(`POST https://playerok.com/rest-api/feature-flags`).

Ручки `/deals/create`, `/steam/*`, `/chats/uncensor-message`,
`/funds-protection/send-email-code` принимают только `multipart/form-data`
и отвечают 415 на JSON. На 400 сервер сам называет недостающие поля —
этим удобно выяснять контракт незнакомой ручки.

GraphQL-схема снята интроспекцией: 104 query, 114 mutation, 18 subscription.
`Item`/`ItemProfile` — интерфейсы (`MyItem`/`ForeignItem`), `UserProfile` — union
из `User` и `UserFragment`. Пагинация курсорная: `Pagination { first, last, before, after }`.
