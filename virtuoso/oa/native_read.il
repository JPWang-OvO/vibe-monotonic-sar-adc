; Read source OA objects without saving or changing their cellviews.
procedure(p0Properties(object)
  foreach(mapcar p object~>prop
    list(p~>name p~>valueType
      sprintf(nil "%L" if(p~>valueType=="hierProp" then p0Properties(p) else p~>value)))))

procedure(p0ReadView(library cell view)
  let((cv shapes ids count result)
    unwindProtect(
      progn(
        cv=dbOpenCellViewByType(library cell view "" "r")
        unless(cv error("Cannot read %s/%s/%s" library cell view))
        shapes=cv~>shapes
        ids=makeTable('p0ShapeIds nil)
        count=0
        foreach(s shapes ids[s]=count count=count+1)
        result=list(
          cv~>cellViewType
          p0Properties(cv)
          foreach(mapcar i cv~>instances
            list(i~>name i~>libName i~>cellName i~>viewName i~>purpose
              i~>xy i~>orient i~>numInst p0Properties(i)
              foreach(mapcar term i~>instTerms list(term~>name term~>net~>name))))
          foreach(mapcar term cv~>terminals
            list(term~>name term~>direction term~>net~>name p0Properties(term)
              foreach(mapcar pin term~>pins
                list(pin~>name pin~>fig~>objType
                  if(pin~>fig~>objType=="inst" then pin~>fig~>name else ids[pin~>fig])
                  p0Properties(pin)))))
          foreach(mapcar net cv~>nets
            list(net~>name net~>sigType net~>isGlobal p0Properties(net)))
          foreach(mapcar s shapes
            list(s~>objType s~>lpp s~>bBox s~>points s~>xy
              s~>theLabel s~>text s~>height s~>justify s~>orient s~>font s~>labelType
              s~>net~>name
              when(s~>parent
                list(s~>parent~>objType
                  if(s~>parent~>objType=="inst" then s~>parent~>name else ids[s~>parent])))
              p0Properties(s)
              when(s~>objType=="path" list(s~>width s~>pathStyle))
              when(s~>objType=="arc" list(s~>ellipseBBox s~>startAngle s~>stopAngle))
              when(s~>objType=="textDisplay"
                list(s~>owner~>objType s~>owner~>name s~>associate~>objType s~>associate~>name
                  s~>isDrafted s~>isOverbar s~>isVisible s~>isNameVisible s~>isValueVisible s~>assocType))))
        )
      )
      when(cv dbClose(cv))
    )
    result
  )
)
