clear all
set more off

global project_root "/Users/rohanpanjwani/School/ECON_1430/Final_Project"
global table_dir "${project_root}/outputs/intermediate/tables/econometrics_reit"
global fig_dir "${project_root}/outputs/intermediate/figures/econometrics_reit"

cap mkdir "${fig_dir}"

import delimited using "${table_dir}/paper_medicaid_terciles_directcare_reit_plot_data.csv", clear

gen tercile_order = .
replace tercile_order = 1 if tercile == "Low"
replace tercile_order = 2 if tercile == "Middle"
replace tercile_order = 3 if tercile == "High"

foreach panel in "National" "Same-state" "Matched" {
    preserve
        keep if panel == `"`panel'"'
        sort tercile_order
        local suffix = cond("`panel'" == "National", "reit_v2", cond("`panel'" == "Same-state", "reit_v2_same_state", "reit_v2_same_state_matched"))
        twoway ///
            (bar coef tercile_order, barw(0.6) color(eltblue)) ///
            (rcap ub lb tercile_order, lcolor(black)), ///
            xlabel(1 "Low" 2 "Middle" 3 "High") ///
            yline(0, lpattern(dash) lcolor(black)) ///
            xtitle("") ///
            ytitle("Coefficient on total nurse HPRD (95% CI)") ///
            title("`panel'") ///
            legend(off) ///
            graphregion(color(white)) ///
            name(g_`=strtoname("`panel'")', replace)
        graph export "${fig_dir}/paper_medicaid_terciles_directcare_reit_`suffix'.png", replace width(1800)
        graph export "${fig_dir}/paper_medicaid_terciles_directcare_reit_`suffix'.pdf", replace
    restore
}

graph combine g_National g_Same_state g_Matched, ///
    cols(3) ///
    title("Medicaid tercile heterogeneity in REIT staffing effects") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_medicaid_terciles_directcare_reit_combined.png", replace width(2800)
graph export "${fig_dir}/paper_medicaid_terciles_directcare_reit_combined.pdf", replace
