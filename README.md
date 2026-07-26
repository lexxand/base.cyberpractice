# Base Cyber Practice

База знаний по информационной безопасности: теория, практика, открытое ПО и
рынок средств ИБ в России.

- [Главный индекс](INDEX.md)
- [Исходник главной страницы сайта](docs/index.md)
- Публичный сайт: <https://lexxand.github.io/base.cyberpractice/>

## Локальный запуск

```bash
uv venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/mkdocs serve
```

Сайт будет доступен по адресу <http://127.0.0.1:8000/>. Строгая проверка
сборки:

```bash
.venv/bin/mkdocs build --strict
```

Публикация выполняется GitHub Actions после push в ветку `main`.
