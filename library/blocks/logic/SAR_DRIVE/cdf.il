
/****************************************************/
 LIBRARY = "MONOTONIC_SAR"
 CELL    = "SAR_DRIVE"
/****************************************************/

let( ( libId cellId cdfId )
    unless( cellId = ddGetObj( LIBRARY CELL )
        error( "Could not get cell %s." CELL )
    )
    when( cdfId = cdfGetBaseCellCDF( cellId )
        cdfDeleteCDF( cdfId )
    )
    cdfId  = cdfCreateBaseCellCDF( cellId )

    ;;; Parameters
    cdfCreateParam( cdfId
        ?name           "scale"
        ?prompt         "scale"
        ?defValue       "1"
        ?type           "string"
        ?parseAsNumber  "yes"
        ?parseAsCEL     "yes"
    )

    ;;; Properties
    cdfId->formInitProc            = ""
    cdfId->doneProc                = ""
    cdfId->buttonFieldWidth        = 340
    cdfId->fieldHeight             = 35
    cdfId->fieldWidth              = 350
    cdfId->promptWidth             = 175
    cdfSaveCDF( cdfId )
)
