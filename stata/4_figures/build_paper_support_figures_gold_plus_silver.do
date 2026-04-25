clear all
set more off

global project_root "/Users/rohanpanjwani/School/ECON_1430/Final_Project"
global table_dir "${project_root}/outputs/intermediate/tables/econometrics"
global fig_dir "${project_root}/outputs/intermediate/figures/econometrics"

cap mkdir "${fig_dir}"

* Gold+silver staffing event-study figures
foreach spec in total_nurse rn {
    use "${table_dir}/csdid_event_`spec'_gold_plus_silver_plot_data.dta", clear
    gen x = .
    replace x = 1 if term == "Tm2"
    replace x = 2 if term == "Tm1"
    replace x = 3 if term == "Tp0"
    replace x = 4 if term == "Tp1"
    replace x = 5 if term == "Tp2"
    keep if inlist(term, "Tm2", "Tm1", "Tp0", "Tp1", "Tp2")

    foreach panel in "National" "Same-state" "Matched" {
        preserve
            keep if panel == `"`panel'"'
            local suffix = cond("`panel'" == "National", "gold_plus_silver_v2", cond("`panel'" == "Same-state", "gold_plus_silver_v2_same_state", "gold_plus_silver_v2_same_state_matched"))
            local title_outcome = cond("`spec'" == "total_nurse", "Total nurse HPRD", "RN HPRD")
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

* Gold+silver stacked-DID RN event-study figures
use "${table_dir}/stacked_event_rn_gold_plus_silver_plot_data.dta", clear
gen x = .
replace x = 1 if term == "Tm2"
replace x = 2 if term == "Tm1"
replace x = 3 if term == "Tp0"
replace x = 4 if term == "Tp1"
replace x = 5 if term == "Tp2"
keep if inlist(term, "Tm2", "Tm1", "Tp0", "Tp1", "Tp2")

foreach panel in "National" "Same-state" "Matched" {
    preserve
        keep if panel == `"`panel'"'
        local suffix = cond("`panel'" == "National", "gold_plus_silver_v2", cond("`panel'" == "Same-state", "gold_plus_silver_v2_same_state", "gold_plus_silver_v2_same_state_matched"))
        twoway ///
            (rcap lb ub x if !missing(lb), lcolor(maroon)) ///
            (connected coef x, lcolor(maroon) mcolor(maroon) msymbol(D)), ///
            xlabel(1 "t-2" 2 "t-1" 3 "t" 4 "t+1" 5 "t+2") ///
            yline(0, lpattern(dash) lcolor(black)) ///
            xtitle("Event time") ///
            ytitle("Coefficient (95% CI)") ///
            title("RN HPRD (stacked DiD): `panel'") ///
            legend(off) ///
            graphregion(color(white))
        graph export "${fig_dir}/stacked_event_rn_`suffix'.png", replace width(1800)
        graph export "${fig_dir}/stacked_event_rn_`suffix'.pdf", replace
    restore
}

* Gold+silver star-rating event-study figures
foreach spec in health_rating overall_rating staffing_rating qm_rating {
    use "${table_dir}/csdid_event_`spec'_gold_plus_silver_plot_data.dta", clear
    gen x = .
    replace x = 1 if term == "Tm2"
    replace x = 2 if term == "Tm1"
    replace x = 3 if term == "Tp0"
    replace x = 4 if term == "Tp1"
    replace x = 5 if term == "Tp2"
    keep if inlist(term, "Tm2", "Tm1", "Tp0", "Tp1", "Tp2")

    local title_outcome = cond("`spec'" == "health_rating", "Health rating", ///
        cond("`spec'" == "overall_rating", "Overall rating", ///
        cond("`spec'" == "staffing_rating", "Staffing rating", "QM rating")))

    foreach panel in "National" "Same-state" "Matched" {
        preserve
            keep if panel == `"`panel'"'
            local suffix = cond("`panel'" == "National", "gold_plus_silver_v2", cond("`panel'" == "Same-state", "gold_plus_silver_v2_same_state", "gold_plus_silver_v2_same_state_matched"))
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

* Gold+silver main staffing coefficient plot
use "${table_dir}/paper_main_coef_plot_data_gold_plus_silver.dta", clear
gen y = .
replace y = 3 if panel == "National"
replace y = 2 if panel == "Same-state"
replace y = 1 if panel == "Matched"

preserve
    keep if outcome == "Total nurse HPRD"
    twoway ///
        (rcap lb ub y, horizontal lcolor(navy)) ///
        (scatter y coef, msymbol(D) mcolor(navy) msize(medlarge)), ///
        ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
        yscale(range(0.5 3.5)) ///
        xline(0, lpattern(dash) lcolor(black)) ///
        xtitle("Estimated post-takeover effect (95% CI)") ///
        title("Total nurse HPRD") ///
        legend(off) ///
        graphregion(color(white)) ///
        name(g_main_total, replace)
restore

preserve
    keep if outcome == "RN HPRD"
    twoway ///
        (rcap lb ub y, horizontal lcolor(maroon)) ///
        (scatter y coef, msymbol(D) mcolor(maroon) msize(medlarge)), ///
        ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
        yscale(range(0.5 3.5)) ///
        xline(0, lpattern(dash) lcolor(black)) ///
        xtitle("Estimated post-takeover effect (95% CI)") ///
        title("RN HPRD") ///
        legend(off) ///
        graphregion(color(white)) ///
        name(g_main_rn, replace)
restore

graph combine g_main_total g_main_rn, ///
    cols(1) ///
    title("Main staffing effects across control designs: gold+silver") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_main_staffing_coefficients_gold_plus_silver.png", replace width(1800)
graph export "${fig_dir}/paper_main_staffing_coefficients_gold_plus_silver.pdf", replace

* Gold+silver Medicaid pretrend diagnostic
use "${table_dir}/paper_medicaid_pretrend_plot_data_gold_plus_silver.dta", clear
gen x = .
replace x = 1 if term == "Tm2"
replace x = 2 if term == "Tm1"
replace x = 3 if term == "Pre_avg"

foreach panel in "National" "Same-state" "Matched" {
    preserve
        keep if panel == `"`panel'"'
        local suffix = cond("`panel'" == "National", "gold_plus_silver_v2", cond("`panel'" == "Same-state", "gold_plus_silver_v2_same_state", "gold_plus_silver_v2_same_state_matched"))
        twoway ///
            (rcap lb ub x if group == "High Medicaid", lcolor(navy)) ///
            (connected coef x if group == "High Medicaid", lcolor(navy) mcolor(navy) msymbol(D)) ///
            (rcap lb ub x if group == "Low Medicaid", lcolor(maroon)) ///
            (connected coef x if group == "Low Medicaid", lcolor(maroon) mcolor(maroon) msymbol(O)), ///
            xlabel(1 "t-2" 2 "t-1" 3 "Pre avg") ///
            yline(0, lpattern(dash) lcolor(black)) ///
            xtitle("Pre-treatment term") ///
            ytitle("Coefficient (95% CI)") ///
            title("Medicaid-group pretrends: `panel'") ///
            legend(order(2 "High Medicaid" 4 "Low Medicaid") rows(1)) ///
            graphregion(color(white))
        graph export "${fig_dir}/paper_medicaid_pretrend_diagnostics_`suffix'.png", replace width(1800)
        graph export "${fig_dir}/paper_medicaid_pretrend_diagnostics_`suffix'.pdf", replace
    restore
}

* Gold+silver descriptive scatter: baseline Medicaid vs staffing change
use "${table_dir}/paper_baseline_medicaid_vs_staffing_change_data_gold_plus_silver.dta", clear
gen label_text = cond(label_flag == 1, label, "")
twoway ///
    (scatter post_minus_pre baseline_medicaid_share, mcolor(navy%55) msymbol(O) msize(medsmall) mlabel(label_text) mlabsize(vsmall) mlabcolor(gs7) mlabposition(0)) ///
    (lfit post_minus_pre baseline_medicaid_share, lcolor(maroon) lwidth(medthick)), ///
    yline(0, lpattern(dash) lcolor(black)) ///
    xtitle("Baseline Medicaid share") ///
    ytitle("Post minus pre total nurse HPRD") ///
    title("Treated facilities: baseline Medicaid dependence and staffing change") ///
    legend(order(2 "Linear fit") rows(1)) ///
    graphregion(color(white))
graph export "${fig_dir}/paper_baseline_medicaid_vs_staffing_change_gold_plus_silver.png", replace width(1800)
graph export "${fig_dir}/paper_baseline_medicaid_vs_staffing_change_gold_plus_silver.pdf", replace

* Gold+silver star-rating coefficient plot
use "${table_dir}/paper_star_main_coef_plot_data_gold_plus_silver.dta", clear
gen y = .
replace y = 3 if panel == "National"
replace y = 2 if panel == "Same-state"
replace y = 1 if panel == "Matched"

foreach outcome in "Health rating" "Overall rating" "Staffing rating" "QM rating" {
    preserve
        keep if outcome == `"`outcome'"'
        local gname = cond("`outcome'" == "Health rating", "g_star_health", ///
            cond("`outcome'" == "Overall rating", "g_star_overall", ///
            cond("`outcome'" == "Staffing rating", "g_star_staffing", "g_star_qm")))
        twoway ///
            (rcap lb ub y, horizontal lcolor(navy)) ///
            (scatter y coef, msymbol(D) mcolor(navy) msize(medlarge)), ///
            ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
            yscale(range(0.5 3.5)) ///
            xline(0, lpattern(dash) lcolor(black)) ///
            xtitle("Estimated post-takeover effect (95% CI)") ///
            title("`outcome'") ///
            legend(off) ///
            graphregion(color(white)) ///
            name(`gname', replace)
    restore
}

graph combine g_star_health g_star_overall g_star_staffing g_star_qm, ///
    cols(2) ///
    title("Main star-rating effects across control designs: gold+silver") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_star_ratings_coefficients_gold_plus_silver.png", replace width(2200)
graph export "${fig_dir}/paper_star_ratings_coefficients_gold_plus_silver.pdf", replace
