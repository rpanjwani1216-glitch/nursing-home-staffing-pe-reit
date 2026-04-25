clear all
set more off

global project_root "/Users/rohanpanjwani/School/ECON_1430/Final_Project"
global table_dir "${project_root}/outputs/intermediate/tables/econometrics"
global fig_dir "${project_root}/outputs/intermediate/figures/econometrics"

cap mkdir "${fig_dir}"

* Clean main staffing coefficient plot
use "${table_dir}/paper_main_coef_plot_data_gold_plus_silver.dta", clear
keep if inlist(outcome, "Total nurse HPRD", "RN HPRD")

gen y = .
replace y = 3 if panel == "National"
replace y = 2 if panel == "Same-state"
replace y = 1 if panel == "Matched"

gen y_plot = y
replace y_plot = y + 0.12 if outcome == "Total nurse HPRD"
replace y_plot = y - 0.12 if outcome == "RN HPRD"

gen outcome_group = 1 if outcome == "Total nurse HPRD"
replace outcome_group = 2 if outcome == "RN HPRD"

twoway ///
    (rcap lb ub y_plot if outcome == "Total nurse HPRD", horizontal lcolor(navy) lwidth(medthick)) ///
    (scatter y_plot coef if outcome == "Total nurse HPRD", msymbol(D) mcolor(navy) msize(large)) ///
    (rcap lb ub y_plot if outcome == "RN HPRD", horizontal lcolor(maroon) lwidth(medthick)) ///
    (scatter y_plot coef if outcome == "RN HPRD", msymbol(O) mcolor(maroon) msize(large)), ///
    ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
    yscale(range(0.5 3.5)) ///
    xline(0, lpattern(dash) lcolor(black)) ///
    ytitle("") ///
    xtitle("Estimated post-takeover effect on staffing HPRD (95% CI)") ///
    title("Main PE staffing effects across control designs") ///
    legend(order(2 "Total nurse HPRD" 4 "RN HPRD") rows(1) pos(6)) ///
    graphregion(color(white))
graph export "${fig_dir}/paper_main_staffing_coefficients_gold_plus_silver_clean.png", replace width(2000)
graph export "${fig_dir}/paper_main_staffing_coefficients_gold_plus_silver_clean.pdf", replace

* Clean Medicaid tercile coefficient plot, one combined figure with 3 panels
import delimited using "${table_dir}/paper_medicaid_terciles_total_nurse_plot_data_gold_plus_silver.csv", clear

gen tercile_order = .
replace tercile_order = 1 if tercile == "Low"
replace tercile_order = 2 if tercile == "Middle"
replace tercile_order = 3 if tercile == "High"
sort panel tercile_order

foreach panel in "National" "Same-state" "Matched" {
    preserve
        keep if panel == `"`panel'"'
        twoway ///
            (bar coef tercile_order, barw(0.6) color(eltblue)) ///
            (rcap ub lb tercile_order, lcolor(black) lwidth(medthick)), ///
            xlabel(1 "Low" 2 "Middle" 3 "High") ///
            yline(0, lpattern(dash) lcolor(black)) ///
            xtitle("") ///
            ytitle("Coefficient on total nurse HPRD (95% CI)") ///
            title("`panel'") ///
            legend(off) ///
            graphregion(color(white)) ///
            name(g_`=strtoname("`panel'")', replace)
    restore
}

graph combine g_National g_Same_state g_Matched, ///
    cols(3) ///
    title("Medicaid tercile heterogeneity in PE staffing effects") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_medicaid_terciles_total_nurse_gold_plus_silver_combined.png", replace width(2400)
graph export "${fig_dir}/paper_medicaid_terciles_total_nurse_gold_plus_silver_combined.pdf", replace
