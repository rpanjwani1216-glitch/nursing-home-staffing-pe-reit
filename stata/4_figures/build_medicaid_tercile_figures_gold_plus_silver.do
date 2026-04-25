clear all
set more off

global project_root "/Users/rohanpanjwani/School/ECON_1430/Final_Project"
global table_dir "${project_root}/outputs/intermediate/tables/econometrics"
global fig_dir "${project_root}/outputs/intermediate/figures/econometrics"

cap mkdir "${fig_dir}"

import delimited using "${table_dir}/paper_medicaid_terciles_total_nurse_plot_data_gold_plus_silver.csv", clear

gen tercile_order = .
replace tercile_order = 1 if tercile == "Low"
replace tercile_order = 2 if tercile == "Middle"
replace tercile_order = 3 if tercile == "High"

foreach panel in "National" "Same-state" "Matched" {
    preserve
        keep if panel == `"`panel'"'
        sort tercile_order
        local suffix = cond("`panel'" == "National", "gold_plus_silver_v2", cond("`panel'" == "Same-state", "gold_plus_silver_v2_same_state", "gold_plus_silver_v2_same_state_matched"))
        graph bar coef, ///
            over(tercile, sort(tercile_order) label(angle(0))) ///
            bar(1, color(eltblue)) ///
            blabel(bar, format(%9.3f) color(black) size(small)) ///
            yline(0, lpattern(dash) lcolor(black)) ///
            title("Medicaid tercile FE DiD: `panel'") ///
            ytitle("Coefficient on total nurse HPRD") ///
            legend(off) ///
            graphregion(color(white)) ///
            name(g_`=strtoname("`panel'")', replace)

        twoway ///
            (bar coef tercile_order, barw(0.6) color(eltblue)) ///
            (rcap ub lb tercile_order, lcolor(black)), ///
            xlabel(1 "Low" 2 "Middle" 3 "High") ///
            yline(0, lpattern(dash) lcolor(black)) ///
            xtitle("") ///
            ytitle("Coefficient on total nurse HPRD (95% CI)") ///
            title("Medicaid tercile FE DiD: `panel'") ///
            legend(off) ///
            graphregion(color(white))
        graph export "${fig_dir}/paper_medicaid_terciles_total_nurse_`suffix'.png", replace width(1800)
        graph export "${fig_dir}/paper_medicaid_terciles_total_nurse_`suffix'.pdf", replace
    restore
}
