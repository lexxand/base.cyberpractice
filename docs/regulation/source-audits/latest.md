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

### IPS-проверка

| Проверка | IPS-запрос | Результат |
|---|---|---|
| Поиск по наименованию в IPS | [запрос](http://pravo.gov.ru/proxy/ips/?list_itself=&x=0&y=0&bpas=cd00000&a1=%CC%E5%F2%EE%E4%E8%EA%E0+%E0%ED%E0%EB%E8%E7%E0+%E7%E0%F9%E8%F9%E5%ED%ED%EE%F1%F2%E8+%E8%ED%F4%EE%F0%EC%E0%F6%E8%EE%ED%ED%FB%F5+%F1%E8%F1%F2%E5%EC&a1type=1&sort=7&page=firstlast&a7type=1&a7date=25.11.2025) | документы не найдены; HTTP 204, bytes=0 |

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

### IPS-проверка

| Проверка | IPS-запрос | Результат |
|---|---|---|
| Поиск по наименованию в IPS | [запрос](http://pravo.gov.ru/proxy/ips/?list_itself=&x=0&y=0&bpas=cd00000&a1=%CC%E5%F2%EE%E4%E8%EA%E0+%E2%FB%FF%E2%EB%E5%ED%E8%FF+%F3%FF%E7%E2%E8%EC%EE%F1%F2%E5%E9+%E8+%ED%E5%E4%E5%EA%EB%E0%F0%E8%F0%EE%E2%E0%ED%ED%FB%F5+%E2%EE%E7%EC%EE%E6%ED%EE%F1%F2%E5%E9+%E2+%EF%F0%EE%E3%F0%E0%EC%EC%ED%EE%EC+%EE%E1%E5%F1%EF%E5%F7%E5%ED%E8%E8&a1type=1&sort=7&page=firstlast&a7type=1&a7date=12.05.2026) | документы не найдены; HTTP 204, bytes=0 |

## Приказ Роскомнадзора от 05.09.2013 № 996 «Об утверждении требований и методов по обезличиванию персональных данных»

- Документ: `rkn-order-996-2013`
- Орган: Роскомнадзор
- Вид: Приказ
- Номер: 996
- Дата: 05.09.2013
- Примечание: IPS по дате/номеру не возвращает приказ № 996. Документ исторический: требования обезличивания заменены приказом Роскомнадзора № 140 от 19.06.2025. Официальный поисковый индекс показывает региональную страницу Роскомнадзора с записью о приказе № 996 и регистрацией Минюста № 29935, но из текущей среды rkn.gov.ru/digital.gov.ru не отвечают до TCP/HTTPS timeout; вторичные источники не используются.

| Ссылка | Результат | Детали |
|---|---|---|
| [Роскомнадзор: региональная официальная страница приказа № 996](https://72.rkn.gov.ru/p21978/p25026/p25052/) | network-error | ConnectTimeout: HTTPSConnectionPool(host='72.rkn.gov.ru', port=443): Max retries exceeded with url: /p21978/p25026/p25052/ (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x…>, 'Connection to 72.rkn.gov.ru timed out. (connect timeout=12)')) |
| [Роскомнадзор: региональный официальный перечень НПА с приказом № 996](https://24.rkn.gov.ru/docs/24/sm38732/Fajl_1.htm) | network-error | ConnectTimeout: HTTPSConnectionPool(host='24.rkn.gov.ru', port=443): Max retries exceeded with url: /docs/24/sm38732/Fajl_1.htm (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x…>, 'Connection to 24.rkn.gov.ru timed out. (connect timeout=12)')) |
| [Минцифры России: карточка приказа № 996](https://digital.gov.ru/documents/prikaz-federalnoj-sluzhby-po-nadzoru-v-sfere-svyazi-informaczionnyh-tehnologij-i-massovyh-kommunikaczij-%E2%84%96-996) | network-error | ConnectTimeout: HTTPSConnectionPool(host='digital.gov.ru', port=443): Max retries exceeded with url: /documents/prikaz-federalnoj-sluzhby-po-nadzoru-v-sfere-svyazi-informaczionnyh-tehnologij-i-massovyh-kommunikaczij-%E2%84%96-996 (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x…>, 'Connection to digital.gov.ru timed out. (connect timeout=12)')) |
| [Актуальный заменяющий приказ Роскомнадзора № 140 в базе знаний](../russia/roskomnadzor/order-140-2025.md) | local-link | Локальная ссылка внутри базы знаний; внешний HTTP-запрос не выполнялся. |

### IPS-проверка

| Проверка | IPS-запрос | Результат |
|---|---|---|
| Точный поиск по дате и номеру | [запрос](http://pravo.gov.ru/proxy/ips/?list_itself=&x=0&y=0&bpas=cd00000&a7type=1&a7date=05.09.2013&a8=996&a8type=2&sort=7&page=firstlast) | документы не найдены; HTTP 204, bytes=0 |
| Поиск по наименованию в IPS | [запрос](http://pravo.gov.ru/proxy/ips/?list_itself=&x=0&y=0&bpas=cd00000&a1=%CE%E1+%F3%F2%E2%E5%F0%E6%E4%E5%ED%E8%E8+%F2%F0%E5%E1%EE%E2%E0%ED%E8%E9+%E8+%EC%E5%F2%EE%E4%EE%E2+%EF%EE+%EE%E1%E5%E7%EB%E8%F7%E8%E2%E0%ED%E8%FE+%EF%E5%F0%F1%EE%ED%E0%EB%FC%ED%FB%F5+%E4%E0%ED%ED%FB%F5&a1type=1&sort=7&page=firstlast&a7type=1&a7date=05.09.2013) | документы не найдены; HTTP 204, bytes=0 |
| Поиск по наименованию в IPS без ограничения даты | [запрос](http://pravo.gov.ru/proxy/ips/?list_itself=&x=0&y=0&bpas=cd00000&a1=%CE%E1+%F3%F2%E2%E5%F0%E6%E4%E5%ED%E8%E8+%F2%F0%E5%E1%EE%E2%E0%ED%E8%E9+%E8+%EC%E5%F2%EE%E4%EE%E2+%EF%EE+%EE%E1%E5%E7%EB%E8%F7%E8%E2%E0%ED%E8%FE+%EF%E5%F0%F1%EE%ED%E0%EB%FC%ED%FB%F5+%E4%E0%ED%ED%FB%F5&a1type=1&sort=7&page=firstlast) | nd=607604898 — Действует без изменений — Постановление Правительства Российской Федерации от 01.08.2025 № 1154. Об утверждении требований к обезличиванию персональных данных, методов обезличивания персональных данных и Правил обезличивания персональных данных<br>nd=607599406 — Действует без изменений — Приказ Федеральной службы по надзору в сфере связи, информационных технологий и массовых коммуникаций от 19.06.2025 № 140. Об утверждении требований к обезличиванию персональных данных и методов обезличивания персональных данных, за исключением случаев, указанных в пункте 9-1 части 1 статьи 6 Федерального закона от 27 июля 2006 г. № 152-ФЗ "О персональных данных" |
