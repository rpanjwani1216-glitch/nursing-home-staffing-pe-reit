# Ownership Transition Verification Notes

This note tracks the integrated `gold_main`, `silver_main`, `silver_unclear`, and `exclude` classifications used in the repo after the 2016–2024 silver expansion pass.

Classification summary:

- `gold_main`: the original verified treatment sample used for the main paper results.
- `silver_main`: explicit PE deal source plus a facility-level platform bridge, but still below the fully verified gold standard.
- `silver_unclear`: likely PE-linked facilities where the pre-period side is financially complex or the sponsor/bridge is still too ambiguous for the main silver sample.
- `exclude`: rows preserved in the integrated master file but outside the active 2016–2024 gold/silver treatment sets.

## PE001: Accordius/Peak/Pelican/Orchid Cove

Post-transition Portopiccolo evidence is visible, but most pre-period structures run through Sava/SSC or Signature-style chains. Rose Manor is the only row currently strong enough for `silver_main`.

Sources: [source 1](https://www.citizen.org/article/nursing-home-transparency/), [source 2](https://www.washingtonpost.com/local/portopiccolo-nursing-homes-maryland/2020/12/21/a1ffb2a6-292b-11eb-9b14-ad872157ebc9_story.html)

### Gold-usable

- `Sunrise Point Health And Rehabilitation Center` (`105250`, `FL`, `Apr 2020`): The current CMS-linked page shows Simcha Hyman and Naftali Zanziper as direct owners since Apr 2020.

### Silver-main

- `Accordius Health At Rose Manor` (`345081`, `NC`, `post-2021 structure visible`): This is the strongest Portopiccolo addition so far because the pre side looks like a localized family/operator structure rather than the Sava/SSC network.

### Silver-unclear

- `Winter Park Care And Rehabilitation Center` (`105332`, `FL`, `Feb 2020 / Apr 2020`): Cleaner than the Sava/SSC examples, but I still have not ruled out PE-style backing on the Signature side, so this stays below the main treatment set for now.
- `Accordius Health At Charlotte` (`345243`, `NC`, `Jan 2020`): Post-transition evidence is strong on ProPublica/CMS.
- `Accordius Health At Gastonia` (`345162`, `NC`, `Dec 2021`): ProPublica lists the Portopiccolo-linked ownership structure from Dec 2021 forward.
- `Accordius Health At Mooresville` (`345179`, `NC`, `Jan 2020`): Post-transition evidence is strong on ProPublica/CMS.

## PE002: Regency Integrated Health Services

Regency is explicitly linked to AHP's Texas platform, and several current CMS pages show public/nonprofit direct owners with Regency managerial control. Missing immediate pre-Regency operator detail keeps the cluster in `silver_main` rather than `gold_main`.

Sources: [source 1](https://www.citizen.org/article/nursing-home-transparency/), [source 2](https://www.akingump.com/en/insights/press-releases/akin-gump-advises-assured-healthcare-partners-in-dollar590m-portfolio-sale)

### Silver-main

- `Bastrop Lost Pines Nursing And Rehabilitation Center` (`676222`, `TX`, `Feb 2016`): Current CMS-linked data clearly show public direct ownership plus Regency managerial control beginning in Feb 2016.
- `Heritage Park Rehabilitation And Skilled Nursing C` (`455599`, `TX`, `Apr 2022`): This is one of the stronger Regency candidates.
- `Memorial City Nursing And Rehabilitation Center` (`676258`, `TX`, `Dec 2022`): Current CMS-linked data show unchanged non-PE direct ownership with Regency managerial control beginning in Dec 2022.
- `Val Verde Nursing And Rehabilitation Center` (`675395`, `TX`, `Apr 2022`): Current CMS-linked data show Regency managerial control from Apr 2022.

### Excluded for Current Build

- `Brenham Nursing And Rehabilitation Center` (`675799`, `TX`, `Feb 2015`): Current CMS-linked data clearly show Oakbend as direct owner and Regency managerial control from Feb 2015.

## PE007: Marquis Health Services

Tryko / Marquis remains the cleanest fully verified nonprofit-to-PE cluster in the repo.

Sources: [source 1](https://www.kaufmanhall.com/news/kaufman-hall-advises-virtua-health-skilled-nursing-facility-transaction), [source 2](https://skillednursingnews.com/2018/07/tryko-partners-acquires-two-baltimore-snfs-plans-multimillion-upgrades/)

### Gold-usable

- `Berlin Rehabilitation & Healthcare Center` (`315461`, `NJ`, `Apr 2022`): A very strong Tryko row.
- `Cambridge Rehabilitation And Healthcare Center` (`315201`, `NJ`, `Jan 2021`): This is another strong target.
- `Mount Holly Rehabilitation & Healthcare Center` (`315128`, `NJ`, `Apr 2022`): This is a clean target.

### Silver-main

- `Collingswood Rehabilitation And Healthcare Center` (`215092`, `MD`, `Feb 2019`): Public deal coverage identifies Tryko Partners as the buyer behind Marquis Health Services' Rockville expansion, naming Collingswood Rehabilitation & Healthcare Center in February 2019.
- `Markley Rehabilitation And Healthcare Center` (`395483`, `PA`, `Dec 2020`): Public deal coverage identifies Tryko Partners as the private equity buyer of Regina Community Nursing Center in December 2020, with the facility rebranded as Markley Rehabilitation & Healthcare Center under Marquis Health Services.
- `Roosevelt Rehabilitation And Healthcare Center` (`395537`, `PA`, `Nov 2019`): Public deal coverage identifies Tryko Partners as the buyer behind the Philadelphia acquisition of Glendale Uptown Home, which was rebranded as Roosevelt Rehabilitation & Healthcare Center in late 2019 under Marquis Health Services.
- `Springfield Rehabilitation And Healthcare Center` (`395690`, `PA`, `Jun 2020`): Public deal coverage identifies Tryko Partners as the buyer behind the Pennsylvania pickup of Harlee Manor, which became Springfield Rehabilitation & Healthcare Center in June 2020 under Marquis Health Services.
- `Canterbury Rehabilitation And Healthcare Center` (`495272`, `VA`, `Feb 2020`): Trade press identifies Tryko Partners as the private equity buyer of Lexington Rehabilitation & Healthcare in Richmond as part of its February 2020 Virginia expansion, with Marquis Health Services as operator.
- `Westmoreland Rehabilitation & Healthcare Center` (`495268`, `VA`, `Feb 2020`): Trade press identifies Tryko Partners as the private equity buyer of Westmoreland Rehabilitation & Healthcare Center in February 2020, with Marquis Health Services as operator.
- `Woodbine Rehabilitation & Healthcare Center` (`495019`, `VA`, `Feb 2020`): Trade press identifies Tryko Partners as the private equity buyer of three Virginia skilled nursing facilities from the Cambridge Healthcare portfolio in February 2020, with Marquis Health Services as operator.

## PE008: Legacy Healthcare

Cascade / Legacy is the strongest expansion cluster: ABCM gives a clean non-PE seller, while current CMS ownership pages repeatedly show Legacy/Cascade post-period control. The silver additions come from the same ABCM portfolio but remain below the original gold verification pass.

Sources: [source 1](https://www.beckershospitalreview.com/post-acute/pe-firm-acquires-29-iowa-nursing-homes-for-85m/), [source 2](https://iowacapitaldispatch.com/2024/10/21/private-equity-firm-buys-29-iowa-nursing-homes-in-massive-85-million-deal/)

### Gold-usable

- `Colonial Manor Of Elma` (`165386`, `IA`, `Aug 2024`): Current CMS-linked ownership shows Iowa Portfolio Opco Holdings LLC and Legacy managerial control since Aug 2024.
- `Concord Care Center` (`165364`, `IA`, `Aug 2024`): The current CMS-linked page shows Legacy managerial control since Aug 2024.
- `Grandview Healthcare Center` (`165340`, `IA`, `Aug 2024`): Another clean Oelwein example.
- `Guttenberg Care Center` (`165334`, `IA`, `Aug 2024`): A clean ABCM-to-Cascade/Legacy transition.
- `Harmony House Health Care Center` (`165152`, `IA`, `Aug 2024`): This Harmony facility is usable and distinct from the weaker Harmony/ManorCare cases.
- `Lake Mills Care Center` (`165366`, `IA`, `Aug 2024`): Strong high-confidence Cascade row.
- `Manor House Care Center` (`165325`, `IA`, `Aug 2024`): Another clean Cascade row.
- `Maple Manor Village` (`165346`, `IA`, `Aug 2024`): A clean ABCM-to-Cascade/Legacy transition.
- `Northgate Care Center` (`165338`, `IA`, `Aug 2024`): Another clean ABCM-to-Cascade/Legacy transition with the same dated ownership and managerial-control pattern as the other Iowa facilities.
- `Oakwood Care Center` (`165365`, `IA`, `Aug 2024`): The older CMS-mirrored page is explicit that Oakwood Care Center was operated by ABCM Corporation in the pre-period, and the current CMS-linked page shows Iowa Portfolio Opco Holdings LLC with Legacy managerial control since Aug 2024.
- `Oelwein Health Care Center` (`165341`, `IA`, `Aug 2024`): The current CMS-linked page shows Legacy managerial control since Aug 2024.
- `Park View Rehabilitation Center` (`165343`, `IA`, `Aug 2024`): Especially useful because the current CMS-linked ownership chain explicitly names Cascade Capital Partners LLC, not just Legacy.
- `Rehabilitation Centers Of Independence West Campus` (`165303`, `IA`, `Aug 2024`): Current CMS-linked ownership shows Iowa Portfolio Opco Holdings LLC and Legacy managerial control since Aug 2024.
- `Valley Vue Care Center` (`165353`, `IA`, `Aug 2024`): This is another clean ABCM-to-Cascade/Legacy transition from the 2024 Iowa portfolio.
- `Westview Care Center` (`165363`, `IA`, `Aug 2024`): This Britt facility follows the same clean ABCM to Cascade/Legacy pattern seen elsewhere in the Iowa portfolio.
- `Westview Of Indianola Care Center` (`165369`, `IA`, `Aug 2024`): The current CMS-linked page directly lists Cascade Capital entities in the indirect ownership chain and Legacy managerial control since Aug 2024.
- `Willow Dale Wellness Village` (`165342`, `IA`, `Aug 2024`): This is another clean ABCM-to-Cascade/Legacy transition.

### Silver-main

- `Bloomfield Care Center` (`165326`, `IA`, `Aug 2024`): Current ProPublica ownership shows Iowa Portfolio Opco Holdings LLC as the direct owner and Legacy Healthcare Financial Services LLC in managerial control since Aug 2024.
- `Emmetsburg Care Center` (`165352`, `IA`, `Aug 2024`): Current ProPublica ownership shows Iowa Portfolio Opco Holdings Llc as the direct owner and Legacy Healthcare Financial Services Llc in managerial control since Aug 2024.
- `Heritage Care And Rehabilitation Center` (`165367`, `IA`, `Aug 2024`): Older CMS-mirrored records clearly show ABCM Corporation as the pre-period owner, while the current page shows Legacy managerial control since Aug 2024.
- `Nora Springs Care Center` (`165347`, `IA`, `Aug 2024`): A strong Cascade candidate.
- `Rehabilitation Center Of Belmond` (`165380`, `IA`, `Aug 2024`): Current ProPublica ownership shows Iowa Portfolio Opco Holdings Llc as the direct owner and Legacy Healthcare Financial Services Llc in managerial control since Aug 2024.
- `Rolling Green Village Care Center` (`165361`, `IA`, `Aug 2024`): A strong candidate from the ABCM portfolio, but I am keeping it one notch below gold because the current CMS-linked page is thinner on the direct-owner fields than the other Iowa facilities.

## PE013: Gold FL Trust II portfolio

Gold FL Trust II is gold-usable when the pre-period owner is clearly local. Facilities with Greystone-era predecessor structures remain `silver_unclear`.

Sources: [source 1](https://projects.propublica.org/nursing-homes/affiliate/a-594), [source 2](https://projects.propublica.org/nursing-homes/homes/h-105640)

### Gold-usable

- `Club Healthcare And Rehabilitation Center At The V` (`106095`, `FL`, `Jul 2022`): Current CMS-linked ownership shows The Club SNF Holdco LLC with Gold FL-related trust entities since Jul 2022.
- `Cypress Care Center` (`105649`, `FL`, `Jul 2022`): Current CMS-linked ownership shows Arbor Nursing Holdco LLC since Mar 2022 with Fl Master Opco Holdco LLC and Fl SNF Trust I/II entering since Jul 2022 on a page affiliated with Gold FL Trust Ii.
- `North Lake Care Center And Rehab` (`105640`, `FL`, `Jul 2022`): Current CMS-linked ownership shows North Lake Nursing Holdco LLC since Mar 2022 with Fl Master Opco Holdco LLC and Fl SNF Trust I/II entering since Jul 2022.
- `Palms Care Center And Rehab` (`105336`, `FL`, `Aug 2023`): Current CMS-linked ownership shows Palms Nursing Holdco LLC with Fl Master Opco Holdco II LLC, Fl SNF Trust I, and Fl SNF Trust II entering since Aug 2023.
- `South Campus Care Center And Rehab` (`105375`, `FL`, `Jul 2022`): Current CMS-linked ownership shows South Campus Nursing Holdco LLC and Fl SNF Trust I/II entering since Jul 2022.
- `Villages Healthcare And Rehabilitation Center, The` (`106099`, `FL`, `Dec 2023`): Current CMS-linked ownership shows The Villages Nursing And Rehab Holdco LLC with Copper FL Trust II, Fl Master Opco Holdco LLC, Gold FL Trust II, and Silver FL Trust II entering since Dec 2023.
- `Williston Care Center And Rehab` (`105467`, `FL`, `Aug 2023`): The current CMS-linked ProPublica ownership listing places the facility in the Gold FL trust structure, and the ProPublica search preview for the same facility shows Williston Nursing Holdco LLC with Fl Master Opco Holdco II LLC and Fl SNF Trust I/II since Aug 2023.

### Silver-unclear

- `Ridgecrest Healthcare And Rehabilitation Center` (`106061`, `FL`, `post-2019 current structure visible`): The current CMS-linked page clearly places the facility in the Gold FL trust structure, but the 2019 page shows Greystone-linked ownership and management.

## PE014: Cypress Healthcare Group

The Eskaton-to-Cypress transition is real, but the sponsor identity still falls short of the project's PE standard, so the entire cluster remains `silver_unclear`.

Sources: [source 1](https://oag.ca.gov/node/572748), [source 2](https://oag.ca.gov/system/files/media/eskaton-conditional-approval-09012023.pdf)

### Silver-unclear

- `Fair Oaks Healthcare Center` (`555153`, `CA`, `Sep 2023`): Current CMS-linked ownership shows Cypress Healthcare Group LLC as the direct owner and Cypress Healthcare Group affiliation since Sep 2023.
- `Greenhaven Healthcare Center` (`555098`, `CA`, `Sep 2023`): Current CMS-linked ownership shows Cypress Healthcare Group LLC as the direct owner and Cypress Healthcare Group affiliation since Sep 2023.
- `Manzanita Healthcare Center` (`555083`, `CA`, `Sep 2023`): Current CMS-linked ownership shows Cypress Healthcare Group LLC as the direct owner and Cypress Healthcare Group affiliation since Sep 2023.

## PE015: RHF California retirement communities

Pacifica / RHF remains an active California gold cluster. Pioneer stays in `gold_main` because it was already accepted into the verified core sample, even though its post-period evidence is secondary-CMS-derived.

Sources: [source 1](https://oag.ca.gov/news/press-releases/attorney-general-bonta-conditionally-approves-sale-four-retirement-communities), [source 2](https://seniorhousingnews.com/2024/04/19/pacifica-adds-15-communities-in-180-5m-deal-as-rhf-shifts-senior-living-strategy/)

### Gold-usable

- `Auburn Ravine Healthcare Center` (`555645`, `CA`, `Feb 2024`): Current CMS-linked ownership shows Auburn Ravine Healthcare Center under Cypress Healthcare Group LLC with managerial control beginning in Feb 2024.
- `Bixby Towers Post-Acute Rehab` (`056283`, `CA`, `Jun 2023`): Current ProPublica ownership now shows Bixby Towers Post Acute Rehab with Jacaranda Healthcare Group LLC as the direct owner since Jun 2023, Aspen Skilled Healthcare Inc as an indirect owner since Nov 2022, and Stephen Thompson in managerial control since Feb 2024.
- `Pioneer House` (`555542`, `CA`, `Jun 2023`): California AG sale materials place Pioneer House in RHF's sale to Pacifica Companies and identify P Street Holdings as the sale designee and Alister LLC as the buyer-side SNF operator.

## PE016: California-Nevada Methodist Homes SNFs

California-Nevada Methodist Homes -> Pacifica is the strongest new public-source Pacifica lead. Lake Park enters `silver_main` because the nonprofit seller, Pacifica buyer, and Aspen-linked post-close chain are all visible, while Forest Hill remains out until the same bridge is clearer.

Sources: [source 1](https://oag.ca.gov/news/press-releases/attorney-general-bonta-conditionally-approves-sale-california-nevada-methodist), [source 2](https://seniorhousingnews.com/2024/04/19/pacifica-adds-15-communities-in-180-5m-deal-as-rhf-shifts-senior-living-strategy/)

### Silver-main

- `Lake Park Healthcare Center` (`555113`, `CA`, `Sep 2023`): California AG materials identify Pacifica Companies LLC as the buyer of California-Nevada Methodist Homes, a nonprofit operator whose Lake Park campus included a 35-bed skilled nursing facility in Oakland.

## PE017: Keiro SNFs

Keiro -> Pacifica / Aspen adds a new California silver cluster. The public sale materials name the nonprofit seller and the two skilled nursing facilities, and the current ProPublica pages show Aspen-linked ownership/control beginning in 2016.

Sources: [source 1](https://seniorshousingbusiness.com/blueprint-arranges-41m-sale-of-642-unit-keiro-portfolio-in-los-angeles/), [source 2](https://www.nichibei.org/2016/06/escrow-closes-but-criticism-of-keiro-sale-continues/)

### Silver-main

- `Kei Ai Los Angeles Healthcare Center` (`555438`, `CA`, `Apr 2016`): Blueprint reports that Pacifica Companies, described as a private investment firm, bought Keiro's four-property Los Angeles portfolio in 2016 and leased the two skilled nursing facilities to Aspen Healthcare.
- `Kei Ai South Bay Healthcare Center` (`555306`, `CA`, `May 2016`): Blueprint reports that Pacifica Companies bought Keiro's Los Angeles portfolio and leased the two skilled nursing facilities to Aspen Healthcare, while Keiro's post-sale notice states that South Bay Keiro Nursing Home became Kei Ai South Bay Healthcare Center under Aspen Skilled Healthcare.
