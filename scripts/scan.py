#!/usr/bin/env python3
"""Сканер сигналов для юридического аудита сайта РФ (152-ФЗ).
Использование:
  python scan.py [путь_к_проекту] [https://сайт]
Ищет в html/js/php-файлах + опц. на живой странице: трекеры, cookie-баннер,
формы сбора ПД, юр-страницы, реквизиты, HTTPS. Выводит сводку сигналов.
Только стандартная библиотека.
"""
import os, re, sys, glob
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
URL = sys.argv[2] if len(sys.argv) > 2 else None

# что ищем: метка -> regex (case-insensitive)
TRACKERS = {
    "Google Analytics (gtag/GA4)": r"gtag\(|googletagmanager\.com|G-[A-Z0-9]{6,}|UA-\d+",
    "Яндекс.Метрика": r"mc\.yandex\.ru|ym\(\d|metrika",
    "Яндекс.Метрика Вебвизор": r"webvisor\s*:\s*true",
    "VK Pixel/Top.Mail": r"vk\.com/rtrg|top-fwz1|tmr\.js|mail\.ru/counter",
    "Facebook/Meta Pixel": r"connect\.facebook\.net|fbq\(",
    "Google Fonts (трансгранично)": r"fonts\.googleapis\.com|fonts\.gstatic\.com",
    "Telegram (внешний сервис)": r"telegram\.org|t\.me/|api\.telegram\.org",
}
PD_FORM = {
    "поле телефона": r'type="tel"|name="[^"]*phone|inputmode="tel"',
    "поле email": r'type="email"|name="[^"]*email',
    "поле ФИО/имя": r'name="[^"]*(name|surname|fio|imya|fam)',
    "поле адреса": r'name="[^"]*(address|adres|delivery)',
    "чекбокс согласия": r'(consent|soglas|agree|personal)["\s][^>]*type="checkbox"|type="checkbox"[^>]*(consent|soglas|agree)',
    "чекбокс предзаполнен (checked)": r'type="checkbox"[^>]*checked|checked[^>]*type="checkbox"',
}
LEGAL = {
    "Политика конфиденциальности": r"политик\w* конфиденциальн|privacy",
    "Согласие на обработку ПД": r"согласи\w* на обработк|обработк\w* персональн",
    "Cookie-баннер/упоминание": r"cookie|куки",
    "Реквизиты: ИНН": r"\b\d{10}\b.{0,20}ИНН|ИНН.{0,3}\b\d{10}\b|inn",
    "Реквизиты: ОГРН": r"ОГРН|ogrn|\b\d{13}\b",
    "Локализация/хранение в РФ": r"территории Российской Федерации|хран\w*.{0,30}РФ|локализац",
    "Трансграничная передача": r"трансгранич",
    "Дата редакции политики": r"редакци\w* от|обновлен\w* от|вступает в силу",
    "Публичная оферта (ГК 437)": r"оферт",
    "Правила возврата товара (ЗОЗПП 26.1)": r"возврат\w* товар|правил\w* возврат|отказ\w* от товар|26\.1",
}
PROHIBITED = {
    "Ссылка на Facebook (Meta запрещена в РФ)": r"facebook\.com|fb\.com|fb\.me|\bfb\.watch",
    "Ссылка на Instagram (Meta запрещена в РФ)": r"instagram\.com|instagr\.am|\big\.me",
}


def collect_text(root):
    parts = []
    files = []
    for ext in ("*.html", "*.js", "*.php", "*.htm"):
        files += glob.glob(os.path.join(root, "**", ext), recursive=True)
    for f in files:
        if os.sep + ".git" + os.sep in f or "node_modules" in f:
            continue
        try:
            parts.append(open(f, encoding="utf-8", errors="ignore").read())
        except Exception:
            pass
    return "\n".join(parts), len(files)


def check(text, groups, title):
    print(f"\n## {title}")
    for label, pat in groups.items():
        hit = re.search(pat, text, re.IGNORECASE)
        print(f"  [{'НАЙДЕНО' if hit else '   нет '}] {label}")


def fetch_url(url):
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "legal-audit-rf"})
    body = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", "ignore")
    scheme = "HTTPS" if url.lower().startswith("https") else "HTTP (!!! ПД по http недопустимо)"
    return body, scheme


def main():
    print(f"# Сигналы для юр-аудита — {os.path.abspath(ROOT)}")
    text, n = collect_text(ROOT)
    print(f"Просканировано файлов: {n}")
    check(text, TRACKERS, "Трекеры / аналитика (риск п.3, п.4 — раскрытие + cookie + трансгранично)")
    check(text, PD_FORM, "Формы сбора ПД (п.2 — согласие; галочка НЕ должна быть предзаполнена)")
    check(text, LEGAL, "Юр-страницы и реквизиты (п.1, п.5, п.6, п.7)")
    check(text, PROHIBITED, "Запрещённые ссылки (п.13 — Meta: Facebook/Instagram запрещены в РФ)")
    if URL:
        try:
            body, scheme = fetch_url(URL)
            print(f"\n## Живой URL: {URL}\n  Протокол: {scheme}")
            check(body, {**TRACKERS, **LEGAL}, "Сигналы на живой странице")
        except Exception as e:
            print(f"\n## Живой URL: ошибка {repr(e)[:150]}")
    print("\n— Интерпретируй сигналы по чек-листу SKILL.md и собери отчёт. —")


if __name__ == "__main__":
    main()
