# Публикация AioScam

## PyPI — ✅ ВЫПОЛНЕНО (Production)

### Информация о публикации

| Параметр | Значение |
|----------|----------|
| **Версия** | 0.1.1 |
| **URL** | https://pypi.org/project/aioscam/ |
| **Дата** | 27 апреля 2026 |
| **Установка** | `pip install aioscam` |
| **Статус** | ✅ Опубликовано и проверено |

### Проверка

```bash
pip install aioscam
python -c "import aioscam; print(aioscam.__version__)"
```

## TestPyPI — ✅ Выполнено

### Информация о публикации

| Параметр | Значение |
|----------|----------|
| **Версия** | 0.1.1, 0.1.1.post1 |
| **URL** | https://test.pypi.org/project/aioscam/ |
| **Дата** | 27 апреля 2026 |
| **Аккаунт** | alexdix (тестовый) |

### Установка

```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ aioscam
```

### Проверка

```python
import aioscam
print(aioscam.__version__)  # 0.1.1.post1

from aioscam import Bot, Dispatcher, Router
from aioscam.filters import Command, F
from aioscam.fsm import State, StatesGroup
from aioscam.utils import KeyboardBuilder

print("✅ Все импорты работают!")
```

### Что включено в пакет

- ✅ 68 модулей фреймворка
- ✅ 35 API методов Max
- ✅ 14 типов событий
- ✅ 9 типов кнопок (inline)
- ✅ 74/74 тестов проходят
- ✅ Документация (RU + EN)
- ✅ py.typed для type hints
- ✅ python-dotenv зависимость

### Процесс публикации

```bash
# 1. Сборка
python -m build

# 2. Загрузка на TestPyPI
twine upload --repository testpypi dist/* \
  --username __token__ \
  --password pypi-YOUR_TOKEN

# 3. Проверка установки
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ aioscam
```

### VPS Деплой

Демо-бот развёрнут на сервере:

| Параметр | Значение |
|----------|----------|
| **Сервис** | aioscam-demo-bot.service |
| **Установка** | aioscam из TestPyPI |

## PyPI — 🟡 Planned

### Требования для публикации

- [x] Тестовая публикация (TestPyPI)
- [x] Документация (RU + EN)
- [x] Type hints (py.typed)
- [x] 74/74 тестов проходят
- [ ] CHANGELOG.md
- [ ] CONTRIBUTING.md
- [ ] Стабильная версия v0.2.0
- [ ] Production тестирование

### Процесс публикации на PyPI

```bash
# 1. Обновить версию
# pyproject.toml: version = "0.2.0"
# aioscam/__init__.py: __version__ = "0.2.0"

# 2. Создать релиз в Git
git tag -a v0.2.0 -m "AioScam v0.2.0"

# 3. Собрать пакет
python -m build

# 4. Загрузить на PyPI
twine upload dist/* \
  --username __token__ \
  --password pypi-YOUR_PYPI_TOKEN
```

### GitHub Actions

Автоматическая публикация настроена в `.github/workflows/publish.yml`:
- Срабатывает при создании release
- Использует trusted publishing (OIDC)
- Не требует токена
