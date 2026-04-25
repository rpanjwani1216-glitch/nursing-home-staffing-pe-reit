clear all
set more off

global project_root "/Users/rohanpanjwani/School/ECON_1430/Final_Project"
global table_dir "${project_root}/outputs/intermediate/tables/econometrics_reit"
global fig_dir "${project_root}/outputs/intermediate/figures/econometrics_reit"

cap mkdir "${fig_dir}"

* REIT event-study figures in the same style as the PE final package
foreach spec in directcare rn {
    use "${table_dir}/reit_csdid_event_`spec'_plot_data.dta", clear
    gen x = event_order + 1

    foreach panel in "National" "Same-state" "Matched" {
        preserve
            keep if panel == `"`panel'"'
            local suffix = cond("`panel'" == "National", "reit_v2", cond("`panel'" == "Same-state", "reit_v2_same_state", "reit_v2_same_state_matched"))
            local title_outcome = cond("`spec'" == "directcare", "Total Nurse HPRD", "RN HPRD")
            twoway ///
                (rcap lb ub x, lcolor(navy)) ///
                (connected coef x, lcolor(navy) mcolor(navy) msymbol(D)), ///
                xlabel(1 "t-2" 2 "t-1" 3 "t" 4 "t+1" 5 "t+2") ///
                yline(0, lpattern(dash) lcolor(black)) ///
                xtitle("Event time") ///
                ytitle("Coefficient (95% CI)") ///
                title("`title_outcome': `panel'") ///
                legend(off) ///
                graphregion(color(white))
            graph export "${fig_dir}/csdid_event_`spec'_`suffix'.png", replace width(1800)
            graph export "${fig_dir}/csdid_event_`spec'_`suffix'.pdf", replace
        restore
    }
}

* Clean main staffing coefficient plot in PE-paper style
use "${table_dir}/paper_main_coef_plot_data_reit.dta", clear
gen y = .
replace y = 2 if panel == "National"
replace y = 1 if panel == "Same-state"
replace y = 0 if panel == "Matched"

gen y_plot = y
replace y_plot = y + 0.10 if outcome == "Direct-care HPRD"
replace y_plot = y - 0.10 if outcome == "RN HPRD"

twoway ///
    (rcap lb ub y_plot if outcome == "Direct-care HPRD", horizontal lcolor(navy) lwidth(medthick)) ///
    (scatter y_plot coef if outcome == "Direct-care HPRD", msymbol(D) mcolor(navy) msize(large)) ///
    (rcap lb ub y_plot if outcome == "RN HPRD", horizontal lcolor(maroon) lwidth(medthick)) ///
    (scatter y_plot coef if outcome == "RN HPRD", msymbol(O) mcolor(maroon) msize(large)), ///
    ylabel(0 "Matched" 1 "Same-state" 2 "National", angle(0)) ///
    yscale(range(-0.5 2.5)) ///
    xline(0, lpattern(dash) lcolor(black)) ///
    ytitle("") ///
    xtitle("Estimated post-takeover effect on staffing HPRD (95% CI)") ///
    title("Main REIT staffing effects across control designs") ///
    legend(order(2 "Total nurse HPRD" 4 "RN HPRD") rows(1) pos(6)) ///
    graphregion(color(white))
graph export "${fig_dir}/paper_main_staffing_coefficients_reit_clean.png", replace width(2000)
graph export "${fig_dir}/paper_main_staffing_coefficients_reit_clean.pdf", replace
