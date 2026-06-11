# =====================================================================
# Hardwise — Capture pin-table export (read-only)  v5
# ---------------------------------------------------------------------
# Exports one CSV row per (part instance, pin) from the ACTIVE OrCAD
# Capture design:
#   refdes,value,footprint,pin_number,pin_name,pin_type,net,page,
#   inst_x,inst_y,nc_marker,off_page
#
# Clean-room implementation written against public Cadence/EMA docs
# ("OrCAD Capture Tcl/Tk Extensions", DBO iterator patterns). Read-only:
# never modifies the design. Run it on public/synthetic designs only —
# CSVs exported from company designs must never enter this repo
# (AGENTS.md hard rule 1).
#
# Usage (Capture 16.6 / 17.x, Windows):
#   1. Open the .dsn in Capture; make it the active project.
#   2. Open the Tcl command window.
#   3. source {C:/path/to/capture_pin_table_export.tcl}
#   4. hardwise_export_pin_table {C:/pin_table.csv}
#
# v5 notes (validated on a real Capture 16.6, 81 pages / 15879 pins):
#   Pins iterated from DboPartInst_NewPinsIter ARE DboPortInst — the v4
#   diagnostic error text named the class. Root cause of the empty
#   columns across v1-v4: 16.6 DBO getters such as GetPinType and
#   GetIsNoConnect take a DboState argument — `$lPin GetPinType $lStatus`.
#   v5 passes it (GetPinNumber "worked" all along only because the
#   CString container happened to fill that argument slot).
#   All other columns confirmed working since v2.
#   Windows Tcl writes CRLF — downstream ingestion must strip \r.
# =====================================================================

proc hw_cstr {} { return [DboTclHelper_sMakeCString] }
proc hw_str {cs} { return [DboTclHelper_sGetConstCharPtr $cs] }

proc hw_csv_quote {s} {
    if {[string first "," $s] >= 0 || [string first "\"" $s] >= 0} {
        return "\"[string map {\" \"\"} $s]\""
    }
    return $s
}

# Capture part-editor electrical types, in enum order. Raw int is kept
# in parentheses so an enum-order mismatch is visible instead of silent.
set ::hw_pin_types {INPUT BIDIRECTIONAL OUTPUT OPEN_COLLECTOR PASSIVE THREE_STATE OPEN_EMITTER POWER}

proc hw_pin_type_name {raw} {
    if {[string is integer -strict $raw] && $raw >= 0 && $raw < [llength $::hw_pin_types]} {
        return "[lindex $::hw_pin_types $raw]($raw)"
    }
    return $raw
}

# Run this and paste the output if pin_type / inst_x / nc_marker columns
# come back empty — it lists every candidate accessor in your release.
proc hardwise_introspect {} {
    puts "=== *Pin* commands ==="
    puts [join [lsort [info commands *Pin*]] \n]
    puts "=== *Location* / *Origin* commands ==="
    puts [join [lsort [info commands *Location*]] \n]
    puts [join [lsort [info commands *Origin*]] \n]
    puts "=== *NoConnect* / *NC* commands ==="
    puts [join [lsort [info commands *NoConnect*]] \n]
    puts [join [lsort [info commands *_GetNC*]] \n]
}

proc hardwise_export_pin_table {{outCsv "pin_table.csv"}} {
    set lStatus  [DboState]
    set lNullObj NULL

    # --- active design ---
    set lDesign $lNullObj
    catch { set lDesign [GetActivePMDesign] }
    if {$lDesign == $lNullObj} {
        catch {
            set lSession $::DboSession_s_pDboSession
            DboSession -this $lSession
            set lDesignsIter [$lSession NewDesignsIter $lStatus]
            set lDesign [$lDesignsIter NextDesign $lStatus]
        }
    }
    if {$lDesign == $lNullObj} {
        puts "hardwise: no active design found — open the .dsn first."
        return
    }

    set fh [open $outCsv w]
    puts $fh "refdes,value,footprint,pin_number,pin_name,pin_type,net,page,inst_x,inst_y,nc_marker,off_page"

    set nPages 0; set nInsts 0; set nPins 0
    # print raw error strings for the first 3 pins — the SWIG type-check
    # error text names the pin object's REAL class, ending the guesswork
    set dbgLeft 3

    # --- schematics (views) ---
    set lViewsIter [$lDesign NewViewsIter $lStatus $::IterDefs_SCHEMATICS]
    set lView [$lViewsIter NextView $lStatus]
    while {$lView != $lNullObj} {
        set lSchematic [DboViewToDboSchematic $lView]
        if {$lSchematic == $lNullObj} {
            set lView [$lViewsIter NextView $lStatus]
            continue
        }

        set lPagesIter [$lSchematic NewPagesIter $lStatus]
        set lPage [$lPagesIter NextPage $lStatus]
        while {$lPage != $lNullObj} {
            incr nPages
            set csPage [hw_cstr]
            catch { $lPage GetName $csPage }
            set pageName [hw_str $csPage]

            # --- net name -> off-page connector name, for this page ---
            array unset offpage
            catch {
                set lOpIter [$lPage NewOffPageConnectorsIter $lStatus]
                set lOp [$lOpIter NextOffPageConnector $lStatus]
                while {$lOp != $lNullObj} {
                    set csOp [hw_cstr]
                    catch { $lOp GetName $csOp }
                    set opName [hw_str $csOp]
                    set lOpNet $lNullObj
                    catch { set lOpNet [$lOp GetNet $lStatus] }
                    if {$lOpNet != $lNullObj} {
                        set csOpNet [hw_cstr]
                        catch { $lOpNet GetNetName $csOpNet }
                        set offpage([hw_str $csOpNet]) $opName
                    }
                    set lOp [$lOpIter NextOffPageConnector $lStatus]
                }
            }

            # --- part instances on this page ---
            set lInstsIter [$lPage NewPartInstsIter $lStatus]
            set lInst [$lInstsIter NextPartInst $lStatus]
            while {$lInst != $lNullObj} {
                set lPlaced [DboPartInstToDboPlacedInst $lInst]
                if {$lPlaced == $lNullObj} {
                    set lInst [$lInstsIter NextPartInst $lStatus]
                    continue
                }
                incr nInsts

                # refdes — direct accessor confirmed in 16.6
                set refdes ""
                if {[catch {
                    set csVal [hw_cstr]
                    $lPlaced GetReferenceDesignator $csVal
                    set refdes [hw_str $csVal]
                }] || $refdes eq ""} {
                    catch {
                        set csName [DboTclHelper_sMakeCString "Part Reference"]
                        set csVal  [hw_cstr]
                        $lPlaced GetEffectivePropStringValue $csName $csVal
                        set refdes [hw_str $csVal]
                    }
                }

                # value — direct accessor confirmed in 16.6
                set value ""
                if {[catch {
                    set csVal [hw_cstr]
                    $lPlaced GetPartValue $csVal
                    set value [hw_str $csVal]
                }] || $value eq ""} {
                    catch {
                        set csName [DboTclHelper_sMakeCString "Value"]
                        set csVal  [hw_cstr]
                        $lPlaced GetEffectivePropStringValue $csName $csVal
                        set value [hw_str $csVal]
                    }
                }

                # PCB footprint — confirmed in 16.6; feeds Hardwise R001
                set footprint ""
                catch {
                    set csVal [hw_cstr]
                    $lPlaced GetPCBFootprint $csVal
                    set footprint [hw_str $csVal]
                }

                # instance origin (ADJUST: three signature candidates)
                set instX ""; set instY ""
                catch {
                    set lPoint [DboTclHelper_sMakeCPoint]
                    $lPlaced GetLocation $lPoint
                    set instX [DboTclHelper_sGetCPointX $lPoint]
                    set instY [DboTclHelper_sGetCPointY $lPoint]
                }
                if {$instX eq ""} {
                    catch {
                        set lPoint [$lPlaced GetLocation $lStatus]
                        if {$lPoint != $lNullObj} {
                            set instX [DboTclHelper_sGetCPointX $lPoint]
                            set instY [DboTclHelper_sGetCPointY $lPoint]
                        }
                    }
                }
                if {$instX eq ""} {
                    catch {
                        set lPoint [DboTclHelper_sMakeCPoint]
                        $lPlaced GetOrigin $lPoint
                        set instX [DboTclHelper_sGetCPointX $lPoint]
                        set instY [DboTclHelper_sGetCPointY $lPoint]
                    }
                }

                # --- pins of this instance ---
                set lPinsIter [$lPlaced NewPinsIter $lStatus]
                set lPin [$lPinsIter NextPin $lStatus]
                while {$lPin != $lNullObj} {
                    incr nPins
                    set pinNum ""; set pinName ""; set pinType ""
                    set netName ""; set ncMark ""

                    catch {
                        set csN [hw_cstr]
                        $lPin GetPinNumber $csN
                        set pinNum [hw_str $csN]
                    }
                    if {[catch {
                        set csN [hw_cstr]
                        $lPin GetPinName $csN
                        set pinName [hw_str $csN]
                    }]} {
                        catch {
                            set csN [hw_cstr]
                            $lPin GetName $csN
                            set pinName [hw_str $csN]
                        }
                    }
                    # v5: 16.6 DBO getters take a DboState argument — the
                    # v4 SWIG error text said it outright ("self status").
                    if {$dbgLeft > 0} {
                        incr dbgLeft -1
                        catch { puts "hardwise-dbg pin#$nPins GetPinType -> [$lPin GetPinType $lStatus] / GetIsNoConnect -> [$lPin GetIsNoConnect $lStatus]" }
                    }
                    if {[catch { set pinType [hw_pin_type_name [$lPin GetPinType $lStatus]] }]} {
                        catch {
                            set lDP [$lPin GetDefiningPin $lStatus]
                            set pinType [hw_pin_type_name [DboSymbolPin_sGetPinType $lDP $lStatus]]
                        }
                    }
                    catch {
                        set lNet [$lPin GetNet $lStatus]
                        if {$lNet != $lNullObj} {
                            set csN [hw_cstr]
                            $lNet GetNetName $csN
                            set netName [hw_str $csN]
                        }
                    }
                    # nc_marker: instance-level NC flag (status arg required)
                    if {[catch { set ncMark [$lPin GetIsNoConnect $lStatus] }]} {
                        catch {
                            set lDP [$lPin GetDefiningPin $lStatus]
                            set ncMark [DboSymbolPin_sGetIsNoConnect $lDP $lStatus]
                        }
                    }

                    set op ""
                    if {$netName ne "" && [info exists offpage($netName)]} {
                        set op $offpage($netName)
                    }

                    puts $fh [join [list \
                        [hw_csv_quote $refdes] [hw_csv_quote $value] \
                        [hw_csv_quote $footprint] \
                        [hw_csv_quote $pinNum] [hw_csv_quote $pinName] \
                        [hw_csv_quote $pinType] [hw_csv_quote $netName] \
                        [hw_csv_quote $pageName] $instX $instY \
                        [hw_csv_quote $ncMark] [hw_csv_quote $op]] ","]

                    set lPin [$lPinsIter NextPin $lStatus]
                }
                catch { delete_DboPartInstPinsIter $lPinsIter }

                set lInst [$lInstsIter NextPartInst $lStatus]
            }
            catch { delete_DboPagePartInstsIter $lInstsIter }

            set lPage [$lPagesIter NextPage $lStatus]
        }
        catch { delete_DboSchematicPagesIter $lPagesIter }

        set lView [$lViewsIter NextView $lStatus]
    }
    catch { delete_DboLibViewsIter $lViewsIter }

    close $fh
    puts "hardwise: wrote $outCsv — pages=$nPages instances=$nInsts pins=$nPins"
}

puts "hardwise pin-table export v5 loaded — run: hardwise_export_pin_table {C:/pin_table.csv}"
puts "v5 fix: DBO getters need a DboState arg; first 3 pins print a one-line sanity check"
