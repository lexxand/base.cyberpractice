# Аудит внешних официальных источников

Этот отчёт показывает документы, которые пока не импортированы как полный
текст или проверяемый официальный HTML/файл. Ошибки сети здесь не являются
доказательством отсутствия документа: они фиксируют, что источник не был
доступен из текущей среды проверки.

Осталось external-документов: **3**.

## Методика анализа защищенности информационных систем

- Документ: `fstec-security-analysis-methodology-2025`
- Орган: ФСТЭК России
- Вид: Методический документ
- Номер: не указан
- Дата: 25.11.2025
- Примечание: Нужна официальная страница/файл ФСТЭК для полного импорта. Из текущей среды fstec.ru не отвечает до TCP/HTTPS timeout; вторичные источники не используются.

| Ссылка | Результат | Детали |
|---|---|---|
| [ФСТЭК России: страница методического документа](https://fstec.ru/dokumenty/vse-dokumenty/spetsialnye-normativnye-dokumenty/metodicheskij-dokument-ot-25-noyabrya-2025-g) | network-error | ConnectTimeout: HTTPSConnectionPool(host='fstec.ru', port=443): Max retries exceeded with url: /dokumenty/vse-dokumenty/spetsialnye-normativnye-dokumenty/metodicheskij-dokument-ot-25-noyabrya-2025-g (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x…>, 'Connection to fstec.ru timed out. (connect timeout=12)')) |

## Методика выявления уязвимостей и недекларированных возможностей в программном обеспечении

- Документ: `fstec-software-vulnerability-methodology-2026`
- Орган: ФСТЭК России
- Вид: Методический документ
- Номер: не указан
- Дата: 12.05.2026
- Примечание: Нужна официальная страница/файл ФСТЭК для полного импорта. Из текущей среды fstec.ru не отвечает до TCP/HTTPS timeout; вторичные источники не используются.

| Ссылка | Результат | Детали |
|---|---|---|
| [ФСТЭК России: страница методического документа](https://fstec.ru/dokumenty/vse-dokumenty/spetsialnye-normativnye-dokumenty/metodicheskij-dokument-ot-12-maya-2026-g) | network-error | ConnectTimeout: HTTPSConnectionPool(host='fstec.ru', port=443): Max retries exceeded with url: /dokumenty/vse-dokumenty/spetsialnye-normativnye-dokumenty/metodicheskij-dokument-ot-12-maya-2026-g (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x…>, 'Connection to fstec.ru timed out. (connect timeout=12)')) |

## Приказ Роскомнадзора от 05.09.2013 № 996 «Об утверждении требований и методов по обезличиванию персональных данных»

- Документ: `rkn-order-996-2013`
- Орган: Роскомнадзор
- Вид: Приказ
- Номер: 996
- Дата: 05.09.2013
- Примечание: IPS по дате/номеру не возвращает приказ № 996. Документ исторический: требования обезличивания заменены приказом Роскомнадзора № 140 от 19.06.2025. Из текущей среды rkn.gov.ru и digital.gov.ru не отвечают до TCP/HTTPS timeout; вторичные источники не используются.

| Ссылка | Результат | Детали |
|---|---|---|
| [Роскомнадзор: региональная официальная страница приказа № 996](https://72.rkn.gov.ru/p21978/p25026/p25052/) | network-error | ConnectTimeout: HTTPSConnectionPool(host='72.rkn.gov.ru', port=443): Max retries exceeded with url: /p21978/p25026/p25052/ (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x…>, 'Connection to 72.rkn.gov.ru timed out. (connect timeout=12)')) |
| [Минцифры России: карточка приказа № 996](https://digital.gov.ru/documents/prikaz-federalnoj-sluzhby-po-nadzoru-v-sfere-svyazi-informaczionnyh-tehnologij-i-massovyh-kommunikaczij-%E2%84%96-996) | network-error | ConnectTimeout: HTTPSConnectionPool(host='digital.gov.ru', port=443): Max retries exceeded with url: /documents/prikaz-federalnoj-sluzhby-po-nadzoru-v-sfere-svyazi-informaczionnyh-tehnologij-i-massovyh-kommunikaczij-%E2%84%96-996 (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x…>, 'Connection to digital.gov.ru timed out. (connect timeout=12)')) |
| [Актуальный заменяющий приказ Роскомнадзора № 140 в базе знаний](../russia/roskomnadzor/order-140-2025.md) | local-link | Локальная ссылка внутри базы знаний; внешний HTTP-запрос не выполнялся. |
