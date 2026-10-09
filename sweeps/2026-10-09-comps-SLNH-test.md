# Mining / HPC Comps Sweep — 2026-10-09
Batch: test:SLNH   Sources: EDGAR + IR (web only)

Local folder not accessible, used web sources only. (Glob of `C:/Users/Jfusc/Desktop/Soluna/**` returned no files from this Linux cloud container.)

## Comparable table
| Ticker | Latest Qtr | Total Rev | Mining Rev (%) | HPC/Hosting Rev (%) | Contracted HPC MW | Energized MW | Pipeline MW | Tenants (term) | Cash | Debt | Converts O/S | Dilution (2Q) | Hashrate EH/s | J/TH | Next Catalyst (date) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SLNH | Q2 2026 (ended 2026-06-30) | $15.06M | $1.72M (11.4% calc)ᵃ | $12.65M (84.0% calc)ᵃ ᵇ; HPC $0ᶜ; Other $0.69M (4.6% calc)ᵈ | Not foundᶜ | ~192 MW (2026-08-01); ~206 MW (2026-09-08)ᵉ | ~6.3 GW total pipeline; >650 MW AI/HPC in development (Kati 2 + Dorothy 3)ᶠ | Galaxy Digital (Kati 1A, 48 MW, term Not found); Bitdeer co-mining (35 MW, term Not found); Metrobloks JV (Kati 2 dev)ᵍ | $113.4M (unrestricted) | $33.1M (carrying) | Green Cloud Note: $7.8M gross / $6.0M carrying, matures 2027-06-20, conv. up to 2.5M sh | 102.5M → 225.8M sh, +120.2% (calc); main source ATM (74.2M sh in Q2) | Not foundʰ | Not found | Annual meeting, vote to raise authorized shares 375M → 1.0B (2026-10-16) |

Footnotes:
- ᵃ Revenue mapping. "Mining Rev" = 10-Q line "Cryptocurrency mining revenue". "HPC/Hosting Rev" = 10-Q line "Data hosting revenue" (the "Data Center Hosting" segment). The 10-Q defines that segment as hosting for third-party **Bitcoin miners**, so this column is bitcoin hosting, not AI/HPC.
- ᵇ Starting in Q2, pass-through electricity is shown gross in revenue. The company says this adds $4.4M to revenue and to cost of revenue. The release does not say how much of the $4.4M sits in the data hosting line.
- ᶜ The separate "High-Performance Computing" segment had no revenue in Q2 2026. No signed HPC/AI lease and no contracted HPC MW were disclosed in the 10-Q, the Q2 release or the 8-Ks filed through 2026-09-28.
- ᵈ Other = "Wind energy generation revenue" $366K + "Demand response service revenue" $321K. Demand response is not a reportable segment; it is a reconciling item. The new Wind segment came from the Briscoe acquisition on 2026-04-01.
- ᵉ These are total operating sites (bitcoin hosting and mining), not HPC. No figure is given at quarter end. 192 MW is as of 2026-08-01. The 206 MW figure (2026-09-08) is after the final 14 MW at Kati 1 was energized.
- ᶠ Company definitions: "approximately 1.6 GW in planning and development" plus "approximately 4.5 GW in assessment with power partners", together "approximately 6.3 gigawatts". Not contracted.
- ᵍ Galaxy and Bitdeer are bitcoin hosting/co-mining counterparties, not HPC tenants. No contract value disclosed for either. Metrobloks is a JV partner, not a tenant.
- ʰ Soluna's own fleet hashrate is not disclosed. Bitdeer's co-mining deployment at Kati 1 is "approximately 2.42 EH/s", but that is customer-owned equipment, so it is not used here.

## Notes: what changed since last quarter
**SLNH**: Revenue rose to $15.06M from $9.39M in Q1 (calc +60%), partly from the new gross presentation of electricity. Acquired the 150 MW Briscoe Wind Farm on 2026-04-01 ($53.0M base price), and Kati 1 is now complete at 83 MW. Galaxy filled 48 MW, and Bitdeer co-mining grew from 28 MW to 35 MW. Funding was heavily dilutive: 74.2M ATM shares in Q2, plus 18.8M ATM shares (~$23.6M) after quarter end. The Yorkville note was redeemed, and Generate Tranches A-1/A-3 ($15.2M principal) were prepaid on 2026-08-10. Still no HPC revenue or HPC lease.

## Evidence
### SLNH
Primary filings:
- Q2 10-Q: https://www.sec.gov/Archives/edgar/data/64463/000162828026056702/slnh-20260630.htm (filed 2026-08-13), with XBRL R-pages under the same folder.
- Q1 10-Q: https://www.sec.gov/Archives/edgar/data/64463/000162828026035538/slnh-20260331.htm (filed 2026-05-15).
- Q2 earnings release, 8-K EX-99.1: https://www.sec.gov/Archives/edgar/data/64463/000149315226037734/ex99-1.htm (filed 2026-08-13).

Fields:
- Latest quarter [Q2 10-Q index, https://www.sec.gov/Archives/edgar/data/64463/000162828026056702/0001628280-26-056702-index.htm, filed 2026-08-13]: Period of Report "2026-06-30".
- Total revenue [Q2 release, 2026-08-13]: "Revenue grew for a fifth consecutive quarter to $15.1 million,". [Q2 10-Q, Statements of Operations (R4)]: total revenue 15,060 ($K), three months ended 2026-06-30.
- Revenue lines [Q2 10-Q, Statements of Operations, $K, three months ended 2026-06-30]: "Cryptocurrency mining revenue" 1,720; "Data hosting revenue" 12,653; "Wind energy generation revenue" 366; "Demand response service revenue" 321; "High-performance computing service revenue" —.
- Segment definition [Q2 10-Q, Segment Information (R23)]: Data Center Hosting revenue is from "hosting services provided to third-party Bitcoin mining customers at the Company's data centers." Demand response "is not included within the four reportable segments."
- Presentation change [Q2 release]: "Effective Q2, pass-through electricity costs are presented on a gross basis in revenue and cost of revenue." and "This presentation change adds $4.4M to each, with no effect on gross profit, operating loss, or net loss."
- Q1 comparison [Q1 10-Q, Statements of Operations, $K]: total revenue 9,394; "Cryptocurrency mining revenue" 2,169; "Data hosting revenue" 6,688; "Demand response service revenue" 537.
- Energized MW [Q2 release]: "As of August 1, 2026, Soluna operated approximately 192 MW across three fully energized sites," and "with an additional 14 MW under construction at Project Kati 1."
- Energized MW, update [8-K EX-99.1, https://www.sec.gov/Archives/edgar/data/64463/000149315226041699/ex99-1.htm, 2026-09-08]: "With Project Kati 1 complete, Soluna's total operating capacity increases to approximately 206 MW".
- Pipeline [Q2 release]: "the Company's development pipeline includes approximately 1.6 GW in planning and development," / "approximately 4.5 GW in assessment with power partners." / "This quarter, we expanded our development pipeline to approximately 6.3 gigawatts,".
- AI/HPC pipeline [8-K, 2026-09-08]: "more than 650 MW of AI and high-performance computing capacity in development at Kati 2 and Project Dorothy 3." / "Kati 2 will add 83 MW for AI and high-performance computing."
- Dorothy 3 [8-K EX-99.1, https://www.sec.gov/Archives/edgar/data/64463/000149315226039781/ex99-1.htm, 2026-08-24]: "Project Dorothy 3, Soluna's planned renewable-first AI computing campus with a potential capacity of up to 300 MW."
- Tenant, Galaxy [Q2 release]: "Kati 1 completed 48 MW of construction on April 1, filled by Galaxy Digital." No term or value disclosed.
- Tenant, Bitdeer [8-K EX-99.1, https://www.sec.gov/Archives/edgar/data/64463/000149315226039964/ex99-1.htm, 2026-08-25]: "Bitdeer will deploy approximately 28 MW of Bitcoin mining equipment." / "The agreement provides for deployment beginning in September 2026, ramping in batches."
- Bitdeer expansion [8-K EX-99.1, https://www.sec.gov/Archives/edgar/data/64463/000149315226044444/ex99-1.htm, 2026-09-28]: "bringing its total deployment at the site to 35 MW and approximately 2.42 EH/s of hash rate" / "The agreement takes the form of a co-mining arrangement," / "is expected to be complete in November 2026." (Note: the fetched exhibit text was labeled "CONFIDENTIAL DRAFT", even though it was filed on EDGAR.)
- Metrobloks JV [Q2 release]: "On June 3, 2026, Soluna entered into a joint venture agreement with Metrobloks to develop Project Kati 2." / "Phase I is a 100 MW critical IT data center development, with Phase II adding a further 250 MW."
- Cash and debt [Q2 release]: "Ended the quarter with $113.4M of unrestricted cash and $33.1M of total debt." [Q2 10-Q balance sheet, $K]: Cash 113,364; "Current portion of debt" 30,103; "Long-term debt" 3,016.
- Debt detail [Q2 10-Q, Debt – Schedule of Total Debt Outstanding (R56), $K, 2026-06-30]: Generate loan 23,145; Green Cloud Note 6,014; Galaxy loan 3,960; Equipment/Land loan 0; total 33,119.
- Converts [Q2 10-Q, Green Cloud Secured Note schedule (R61), $K]: "Convertible note" 7,803; "Total outstanding note" 6,014; "Interest Rate" 9.00%. [Q2 10-Q, Debt note (R16)]: "The Green Cloud Note matures on June 20, 2027." / "the Green Cloud Note is now convertible into up to 2,500,000 shares of the Company's common stock".
- Debt after quarter end [Q2 10-Q, Subsequent Events (R24)]: "prepaid in full the Tranche A-1 Loans and Tranche A-3 Loans, respectively." The prepayment was on 2026-08-10 and covered $15.2M of principal plus an ~$3.9M premium.
- Shares, 2025-12-31 [Q2 10-Q balance sheet]: "102,531,089 shares outstanding as of December 31, 2025".
- Shares, 2026-03-31 [Q1 10-Q balance sheet]: "111,803,635 shares issued and 111,717,040 shares outstanding as of March 31, 2026".
- Shares, 2026-06-30 [Q2 10-Q balance sheet]: "225,821,479 shares outstanding as of June 30, 2026". Cover page: "As of August 10, 2026, the Registrant had 244,590,575 shares of common stock outstanding."
- Dilution (calc): 225,821,479 − 102,531,089 = +123,290,390 shares (+120.2%) over two quarters. Q2 alone: 111,717,040 → 225,821,479 (+102.1%).
- Dilution sources [Q2 10-Q, Statement of Changes in Equity (R5), Q2 2026]: "Issuance of shares- ATM settlements, (in shares)" 74,174,213; "Issuance of shares-Restricted stock awards (in shares)" 20,510,835; "Issuance of shares- SEPA draws (in shares)" 10,237,605; "Issuance of shares - Series B conversion (in shares)" 5,957,291; "Issuance of shares - warrant exercise (in shares)" 3,239,951. Q1 2026: "Issuance of shares - warrant exercise (in shares)" 8,149,200.
- ATM proceeds [Q2 10-Q, Cash Flows (R6), six months ended 2026-06-30, $K]: "Proceeds from sale of common stock on ATM" 113,465; "Proceeds from sale of common stock on SEPA" 18,928.
- ATM after quarter end [Q2 10-Q, Subsequent Events (R24)]: "issued 18,769,096 shares of common stock pursuant to the ATM Agreement" (~$23.6M net).
- Hashrate / J/TH: Not found. No company-fleet hashrate or efficiency appears in the Q2 10-Q, the Q2 release or the 8-Ks from Jul–Sep 2026. Mining continues: the release says revenue was "partially offset by hashprice compression." No wind-down is disclosed.
- Next catalyst [DEF 14A, https://www.sec.gov/Archives/edgar/data/64463/000162828026058611/slnh-20260824.htm, filed 2026-08-24]: meeting on "October 16, 2026, at 10:00 a.m., Eastern Time." The proposals raise authorized common shares from 375,000,000 to 1,000,000,000 and approve issuance of "20% or more of the Company's issued and outstanding shares" under the YA II PN SEPA.
- Other dated items: the Bitdeer 35 MW expansion is expected to complete in November 2026 (8-K, 2026-09-28). The Q3 2026 earnings date was not found.
