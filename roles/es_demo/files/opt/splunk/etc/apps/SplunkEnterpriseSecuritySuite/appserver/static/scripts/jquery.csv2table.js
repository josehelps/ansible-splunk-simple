//@utf-8

(function($) {

	$.csv2table={
		name     : 'csv2table',
		version  : '0.02-b-2.8',
		date     : '2009.1.10',
		update   : 'http://jsgt.org/lib/jquery/plugin/csv2table/v002/update.txt',
		ver      : '<span class="csv2tableVersion" style="color:#aaa"></span><script>jQuery(function($){ $(".csv2tableVersion").html("version:csv2table-"+$.csv2table.version) })</script>',

		charset  : 'utf-8',  
		doc      : 'http://jsgt.org/mt/01/',
		demo     : 'http://jsgt.org/lib/jquery/plugin/csv2table/v002/test.htm',
		author   : 'Toshiro Takahashi',
		lisence  : 'Public Domain',
		loadImg  : (new Image()).src='./img/icon-loadinfo.gif',  //Dafault loading IMG 
		sortNImg : (new Image()).src='./img/icon-n.gif',         //Dafault sort IMG N
		sortDImg : (new Image()).src='./img/icon-d-green.gif',   //Dafault sort IMG D 
		sortAImg : (new Image()).src='./img/icon-a-green.gif',   //Dafault sort IMG A
		setting  : [],
		data     : [],
		_rowsAry : [],
		_doc     : document,
		err      : [],
		f        : {
			classifyByCol:function(id,colIndex,myCompAry,nolegend){
				var toj=$('table',$('#'+id)),oj=$('tr > td:nth-child('+(colIndex+1)+')',toj)
				if(!nolegend){
					var legend=($('#csv2table-legend-'+id).length==0)?
						$('<div class="csv2table-legends" id="csv2table-legend-'+id+'"></div>'):$('#csv2table-legend-'+id);
					toj.after(
						legend.append(
							$('<div class="csv2table-legends" id="csv2table-legend-'+id+'-'+colIndex+'"></div>')
							.append($.csv2table._rowsAry[id][0][colIndex]+' ')
						)
					)
				}
				//Eg. myCompAry is [['>10','#eee'],['>30','#ddd'],['>50','#bbb']]
				$.each(myCompAry,function(){
					oj
					.filter(':_csv2table_myComp('+this[0]+')')
					.css('background',this[1])
					if(!nolegend){
						var hanrei='<span style="background-color:'+this[1]+'">'
						          +'&nbsp;&nbsp;&nbsp;&nbsp;</span> '
						$('#csv2table-legend-'+id+'-'+colIndex)
							.append(hanrei+this[0].split('<').join('&lt;')+'&nbsp;&nbsp;&nbsp;' )
					}
				})
				
			}
		}
	}



	$.fn.csv2table= function (url,setting){ 

		if(!setting)var setting={};
		var contents=$.fn.csv2table.el=this,id=this[0].id,
		op = $.csv2table.setting[id] = $.extend({
			url                : url,
			nowloadingImg      : $.csv2table.loadImg,              //Image of now loading...
			nowloadingMsg      : 'now loading...',                 //Massege of  now loading...
			sortNImg           : $.csv2table.sortNImg,             //Sort IMG N
			sortDImg           : $.csv2table.sortDImg,             //Sort IMG D
			sortAImg           : $.csv2table.sortAImg,             //Sort IMG A
			removeDoubleQuote  : true,                             // remove " of "hogehoge"
			appendThead        : null,                             //Array. Append a Row of Thead.(e.g. ["Name","Address"]) 
			col_midasi         : 0,                                //
			row_sep            : '\n',                             //Separator of rows. default '\n'
			col_sep            : ',',                              //Separator(,|\t|;) of cols. default ','
			sortable           : true,                             //col sort
			select             : '*',                              //select col lists. default '*' is all cols.
			orderBy            : null,                             //array of sort col. orderBy:[[colNo|'colName','sortType']]
			where              : null,                             //array of where : [{'ColName':'condition'}] etc.
			limit              : null,                             //array of limit : [offset,len]
			col0color          : true,                             //col[0] color sync jQchart line_strokeStyle
			numArignRight      : true,                             //Set the Number TD to "textAlign : 'right'"
			onload             : null,                             //collback function (id,op,data,ary) {}
			use                : null,                             // 'jqchart:line#canvasID'
			className_div      : 'csv2table-div',                  //className 
			className_table    : 'csv2table-table',                //className 
			className_table_th : 'csv2table-table-th',             //className 
			className_table_td : 'csv2table-table-td',             //className 
			className_hoboNum  : 'csv2table-hoboNum',              //className 
			className_sortMark : 'csv2table-sortMark',             //className 
			className_legends  : 'csv2table-legends'               //className
		},setting);

		if(op.row_sep=='\n')op.row_sep_reg='\r\n'
		if(op.use){
			op.use_api      = op.use.split(':')[0]
			op.use_api_type = op.use.split('#')[0]
			op.use_api_box  = op.use.split(':')[1].split('#')[1]
		}

		//Custom Selectors
		$.extend($.expr[":"], {
			//_csv2table_hoboNum is match to number or Number-like (3 digit + comma)
			//for Set the Number TD to "textAlign : 'right'"
			_csv2table_hoboNum  : function(a,i,m){ 
				var b = a.textContent||a.innerText||$(a).text()||"",
					c = Number(
						chkThreeComma(b).split(",").join("")
					); 
				return !isNaN(b) || !isNaN(c);
			},
			//
			_csv2table_myComp  : function(a,i,m){ 
				var b = Number(
					(a.textContent||a.innerText||$(a).text()||"")
						.replace(" ","")
						.replace(/,/g,'')
				);
				return typeof b=='number'? eval(b+m[3]):false;
			}
		});

		$(contents).before('<div class="csv2table-loading"><img src="'+op.nowloadingImg+'"> '+op.nowloadingMsg+' </div>' )

		$.get(url+"?"+(new Date()).getTime(),"",function(data,textStatus){
			if(op.appendThead)data=op.appendThead.join(op.col_sep)+op.row_sep+data;
			$.csv2table.data[id]=data;
			$(".csv2table-loading").fadeOut();
			$(contents).css("display","none").html(mkRowsAry(id,data));
			setCSS(id);
			$(contents).fadeIn();
			if(op.use_api=='jqchart'){
				if(op.use_api_type=='jqchart:line')op.type=$.csv2table.setting[id].type='line';
				else if(op.use_api_type=='jqchart:bar')op.type=$.csv2table.setting[id].type='bar';
				useChart(id,op,data,$.csv2table._rowsAry[id]);
			}
			if($.csv2table.setting[id].onload)$.csv2table.setting[id].onload(id,op,data,$.csv2table._rowsAry[id]);
		});

		$.csv2table.wrtTable=function(colIndex,id,callback){
			$("#"+id).html(mkRowsAry(id,$.csv2table._rowsAry[id],op['th'+colIndex],colIndex));	
			setCSS(id);
			if(op.use_api=='jqchart'){
				if(op.use_api_type=='jqchart:line')op.type=$.csv2table.setting[id].type='line';
				else if(op.use_api_type=='jqchart:bar')op.type=$.csv2table.setting[id].type='bar';
				useChart(id,op,$.csv2table.data[id],$.csv2table._rowsAry[id]);
			}
			if($.csv2table.setting[id].onload)$.csv2table.setting[id].onload(id,op,$.csv2table.data[id],$.csv2table._rowsAry[id]);
			if(callback)callback(op['th'+colIndex],colIndex,id);
		}

		$.csv2table.reset=function(id){
			rowsAry=$.csv2table._rowsAry[id]=escapeStrComma(op.col_sep,op.row_sep,$.csv2table.data[id],op.removeDoubleQuote);
			$("#"+id).html( mkTable(id,rowsAry));
			if(op.sortable)$('#'+id+' table th .sortimg').attr('src',op.sortNImg )
			setCSS(id);
			if(op.use_api=='jqchart'){
				if(op.use_api_type=='jqchart:line')op.type=$.csv2table.setting[id].type='line';
				else if(op.use_api_type=='jqchart:bar')op.type=$.csv2table.setting[id].type='bar';
				useChart(id,op,$.csv2table.data[id],$.csv2table._rowsAry[id]);
			}
		}

		function orderWk(ary,sortType,colIndex){
			ary.head=ary.slice(0,op.col_midasi+1) 
			var rowsAry=ary.slice(op.col_midasi+1,ary.length) 
			rowsAry=sortwk(rowsAry,sortType,colIndex);
			rowsAry=ary=ary.head.concat(rowsAry)
			return rowsAry
		}

		function mkRowsAry(id,data,sortType,colIndex){  

			var rowsAry=null,rewrite=true,//zanntei
				ofs,len
			
			if(sortType && rewrite){
				rowsAry=$.csv2table._rowsAry[id]=orderWk(data,sortType,colIndex);
			} else {
				rowsAry=$.csv2table._rowsAry[id]=escapeStrComma(op.col_sep,op.row_sep,data,op.removeDoubleQuote);
					
				if(op.where){ 
					var _rowsAry = rowsAry,
						rowsAry  = [],
						wlen     = op.where.length-1,
						colNamesArry =_rowsAry[0] ;
					for(var i=_rowsAry.length-1 ;i> 0;i--){ //最終行はheaderなので無視
					
						var sikis='',siki='',colValue='',value='',colNo=null;
						for(var j=0,ok=false;j<=wlen;j++){
							if(op.where[j]=='&&' || op.where[j]=='||'){
								siki =op.where[j];
								sikis += " " +siki;ok=true;
							} else {

								if(typeof op.where[j].length=='number'){
									colNo=op.where[j][0]; value=$.trim(op.where[j][1]);
								} else if(typeof op.where[j]=='object'){
									for(var k in op.where[j]){
										var colName=$.trim(k);value=$.trim(op.where[j][k]);break;
									}
									colNo= $.inArray(colName, colNamesArry);//get colNo 
																		
								} else ok=errLog('op.where operetor');

									if(value.match(/^==(.*)/g)){
										siki = '"'+_rowsAry[i][colNo]+'"=="'+RegExp.$1+'"'; 
										sikis += " " +siki;ok=true;

								} else if(value.match(/^like\s*(.*)/g)){

									var reg= RegExp.$1;
										reg= reg.split('\\_').join('###adrsr###') ; //escape _
										reg= reg.replace(/_/g,'.') ; 
										reg= reg.split('###adrsr###').join('_') ; 
										reg= reg.split('\\%').join('###parst###') ; //escape %
										reg= reg.replace(/%/g,'.*') ; 
										reg= reg.split('###parst###').join('%') ; 
										reg= '^'+reg+'$' ; 
									siki=(_rowsAry[i][colNo].match(new RegExp(reg,'g')))?true:false;
									sikis += " " +siki;ok=true;
								
								} else if(chkThreeComma(_rowsAry[i][colNo])){
									colValue=_rowsAry[i][colNo].split(',').join('');
									siki = colValue+value.split(',').join(''); 
									if(chkSiki(siki) != null){ 
										sikis += " " +siki;ok=true;
									} else ok=errLog('op.where operetor');
								
								} else {
									colValue= _rowsAry[i][colNo] ;
									siki = colValue+value; 
									if(chkSiki(siki) != null){ 
										sikis += " " +siki;ok=true;
									} else ok=errLog('op.where operetor');
								}
							}
						}

						if(eval(sikis) && ok)rowsAry.unshift(_rowsAry[i]);
					}
					rowsAry.unshift(_rowsAry[0]); 
					$.csv2table._rowsAry[id]=rowsAry;
				}

				resetSortImg(id);
				if(op.orderBy){
					var cv,orderlen = op.orderBy.length-1;
					for(var i=orderlen ;i>=0;i--){
						var cv=getColNoAndValue(op.orderBy[i],rowsAry[0]);
						rowsAry=$.csv2table._rowsAry[id]=orderWk(
							rowsAry,cv.val,cv.cln
						)
					}
				} 
				
				if(op.limit){
					var lmt=op.limit,lmlen=lmt.length,_rowsAry=[],zan,end;
					if(lmlen==1)ofs=1,len=lmt[0];
					else if(lmlen==2)ofs=lmt[0]+1,len=lmt[1];
					else ofs=1,len=rowsAry.length;
					zan=rowsAry.length-ofs;
					if(len>zan)len=zan;
					end=ofs+len;
					for(var i=rowsAry.length;i>0;i--){
						if(ofs<=i && i<end)_rowsAry.unshift(rowsAry[i]);
					}
					_rowsAry.unshift(rowsAry[0]);
					rowsAry=$.csv2table._rowsAry[id]=_rowsAry;
				}
			}
			
			var tableHtm=mkTable(id,rowsAry);

			return tableHtm;
		}
		
		function errLog(msg){
			$.csv2table.err.unshift('[Err] '+msg) ;
			return false;
		}
		
		function getColNoAndValue(opr,colNamesArry){ 
			var colNo=null,value=null;
			if(typeof opr[0]=='number')colNo=opr[0]; 
			else if(typeof opr[0]=='string')
				colNo= $.inArray($.trim(opr[0]),colNamesArry); 
			value=$.trim(opr[1]);
			return {cln:colNo,val:value}
		}
		
		function chkCompOpr(siki){
			return siki.match(/^&&|\|\|$/g) && siki.length==2
		}

		function chkSiki(siki){
			return siki.match(/^[0-9]*[<>\!=][=]{0,}[0-9]*$/g)
		}

		function  mkTable(id,rowsAry){
			if(!rowsAry)return 
			var row=rowsAry.length,col=rowsAry[0].length,
				s=op.col_midasi+1
			var htm="";

			//見出し行の処理
			htm+= "<tr>";
			for (var k=0; k<col; k++) {

				var si=$('#'+id+'-sortimg-'+k)[0],
					sortimgsrc=(si)?$('#'+id+'-sortimg-'+k)[0].src:op.sortNImg;
				if(op['th'+k]!=null)
					 if(op['th'+k]=='D')sortimgsrc=op.sortDImg;
				else if(op['th'+k]=='A')sortimgsrc=op.sortAImg;
				else if(op['th'+k]=='N')sortimgsrc=op.sortNImg;

				htm+= "<th id='"+id+"-th-"+k+"'>"
				   + rowsAry[op.col_midasi][k];

				if(op.sortable)
				htm+= "<img id='"+id+"-sortimg-"+k+"' class='sortimg' src='"+sortimgsrc+"' border='0'>"
				htm+= "</th>";

				if(!op['th'+k])op['th'+k]=null;//memo of sortType
			}
			htm+= "</tr>";
				
			//data行の処理
			for (var i=s; i<row; i++) {
					htm+= "<tr>";
					//列の処理
					for (var j=0; j<col; j++) {
						htm+= "<td>"
						   + rowsAry[i][j]
						   + "</td>";
					}
					htm+= "</tr>";
			}

			var tableHtm=$.csv2table._doc.getElementById(id)
				.innerHTML="<table>"+htm+"</table>";

			return tableHtm;

		}
		
		
		////
		// 並べ替え
		// @parame dataAry    並べ替え対象配列
		// @parame sortType   昇順A|降順D
		// @parame colIndex   ソート列
		//
		function sortwk(dataAry,sortType,colIndex){

			if(!dataAry)return ;

			sortType=sortType.toUpperCase();
			if(sortType=="D")op['th'+colIndex]='D';
			else op['th'+colIndex]='A';

			var ci=colIndex,
				are3comma=chkThreeComma(dataAry[0][ci]),
				mved3comma=are3comma.split(",").join("");
			if(!isNaN(dataAry[0][ci]) || !isNaN(mved3comma)){
				var rowlen=dataAry.length;
				if(are3comma != 'null'){ 
					for(var j=0;j<rowlen;j++){
						var d=chkThreeComma(dataAry[j][ci]).split(",").join("") ;
						dataAry[j].unshift((isNaN(d))?0:d);
					}
					ci=0;
				}

				(sortType=="D")?
				dataAry.sort(function (a,b){ 
						return (b[ci] - a[ci]) ;//降順 
				}):
				dataAry.sort(function (a,b){ 
						return (a[ci] - b[ci]);// 昇順
				})

				if(are3comma != 'null'){ 
					for(var j=0;j<rowlen;j++)dataAry[j].shift();
				}

			} else { 
				dataAry.sort(
					function(a,b){
	
						if(!a[ci]) { 
							if(!b[ci])return 0;
							else     return 1;
						} else if(!b[ci]) {
							return -1;
						}
						
						if(""+a[ci] === ""+b[ci])return 0;
						return (sortType=="D")?
							((""+a[ci] > ""+b[ci])?-1:1):
							((""+a[ci] > ""+b[ci])?1:-1);
					}
				)
			}
			return dataAry;
		}
		
		function escapeStrComma(col_sep,row_sep,oj,removeDoubleQuote){
			var rdq=(removeDoubleQuote)?'':'"';

			//mk dmy for comma in "
			var dmy =['-###','###-'],cnt=0,r;
			cnt=(function mkdmy(cnt){
				if(!(
					oj.indexOf((dmy[0]+'comma'+cnt+dmy[1]))==-1 ||
					oj.indexOf((dmy[0]+'rn'+cnt+dmy[1]))==-1 ||
					oj.indexOf((dmy[0]+'wDquote'+cnt+dmy[1]))==-1 
				))mkdmy( ++cnt )
				else void(0)
				return cnt;
			})(cnt)

			var reg='(["](.|(\r\n))*?(["]$|["][,('+op.row_sep_reg+')]))',
				dmystr_comma=''+(dmy[0]+'comma'+cnt+dmy[1]) ,
				dmystr_rn=''+(dmy[0]+'rn'+cnt+dmy[1]) ,
				dmystr_wDquote=''+(dmy[0]+'wDquote'+cnt+dmy[1]) ;

			escape= oj.replace('""',dmystr_wDquote);
			escape= escape.replace(
				new RegExp(reg,"g"),
				function (after,before,index) {
					after= after
							.replace(/(\r\n)(?!$)/g,dmystr_rn)
							.replace(/,(?!$)/g,dmystr_comma)
					return after
					
				}
			)

			if(op.select == '*'||op.select == ['*'])
					r=$.csv2table._rowsAry[id]=mkArray(escape,op.col_sep,op.row_sep);
			else	r=$.csv2table._rowsAry[id]=mkSelectedArray(escape,op.col_sep,op.row_sep,op.select)

			var b=[],rowlen=r.length,collen=r[0].length;
			for(var i=0;i<rowlen;i++){
				if(r[i]=='')continue; 
				b[i]=r[i];
				for(var j=0;j<collen;j++){
					try{
						b[i][j]=$.trim(r[i][j])
							.replace(/^"|"$/g,rdq)
							.replace(new RegExp(dmystr_comma,"g"),",")
							.replace(new RegExp(dmystr_rn,"g"),"\r\n")
							.replace(new RegExp(dmystr_wDquote,'g'),'""');
					} catch(e){}
				}
			}
			return b
		}
		
		function mkSelectedArray(data,col_sep,row_sep,select){
				var rows=data.split(row_sep),rc=[],c=[],
				    rowlen=rows.length ;
				for(var i=0;i<rowlen;i++){
					if($.trim(rows[i])=='') continue; 
					try{
						rc[i]=rows[i].split(col_sep);
						c[i]=[];
						for(var j=0;j<select.length;j++){
							c[i].push(rc[i][select[j]])
						}
					} catch(e){ }
				}
				return c||rc
		}


		function mkArray(data,col_sep,row_sep){
				var rows=data.split(row_sep),rc=[]
				    rowlen=rows.length ;
				for(var i=0;i<rowlen;i++){
					if($.trim(rows[i])=='') continue; 
					try{
						rc[i]=rows[i].split(col_sep);
					} catch(e){ }
				}
				return rc
		}
		
		function setDefault(settingName,val){
			var prop = (setting[settingName]=='undefined'||
				 setting[settingName]==null)?val:setting[settingName]
			return prop
		}

		function chkThreeComma(data){
			return data.replace(" ","")
						.split(".")[0]
						.match(/^[0-9]{1,3}(,[0-9]{3})*,[0-9]{3}$/g)+"" 
		}


		function setCSS(id){
			$('#'+id+'').css({
				/*backgroundColor  : '#eee',
				border           : '1px solid #555',*/
				padding          : '0px', 
				margin           : '1px'
			}).addClass(op.className_div)
			
			$('#'+id+' table').css({
				borderCollapse   : 'collapse',
				borderSpacing    : '0px',
				marginBottom     : '10px'
			}).addClass(op.className_table)
			
			$('#'+id+' table th').css({
				borderColor      : '#eee #999 #777 #bbb',
				borderStyle      : 'solid',
				borderWidth      : '1px',
				backgroundColor  : '#ccc', 
				fontSize         : '12px',
				padding          : '4px',
				textAlign        : 'center'
			}).addClass(op.className_table_th)
			
			$('#'+id+' table td').css({
				borderColor      : '#eee #aaa #999 #ccc',
				borderStyle      : 'solid',
				borderWidth      : '1px',
				padding          : '8px',
				fontSize         : '12px'
			}).addClass(op.className_table_td)
			
			var numTD=$('#'+id+' table td:_csv2table_hoboNum')
				.addClass(op.className_hoboNum)
			if(op.numArignRight)numTD.css({
				textAlign        : 'right'
			})

			if(op.sortable){
				$('#'+id+' table th')
					.css('font-family','Arial')
					.css('text-decoration','none')
					.addClass(op.className_sortMark)
					.each(function (i,el) {
						var i =$('#'+id+' table th').index(this);
						$(this).click(function (e) {
							resetSortImg(id,i);
							if(op['th'+i]=='D') op['th'+i]='A';
							else op['th'+i]='D';
							$.csv2table.wrtTable( i,""+id+"",function(sortType,colIndex,id){});
						});
					}); 
			}
		}

		function resetSortImg(id,index){
			var thlen=$.csv2table._rowsAry[id][0].length;
			for(var i=0;i<thlen;i++)if(i!=index){ op['th'+i]='N'}
			$('#'+id+' table th img.sortimg').each(function(){
				$(this).attr('src',$.csv2table.setting[id].sortNImg );
			})
		}

		function useChart (id,op,data,ary){
			var head= ary[0],dataBody=ary.slice(1) ;
			$("#"+op.use_api_box).jQchart({
				config : $.extend(op,{ 
					width    : $('#'+id+' table').width()+10,
					paddingL : $('#'+id+' table th:nth-child(1)').width()+14,
					labelX   : (op.labelX=='useChart')?head.slice(1):op.labelX,
					onload   : ($.csv2table.setting[id].onload)?$.csv2table.setting[id].onload(id,op,data,ary):null
				}),
				data : (function(){
					var d = [];
					for(var i=0,len=dataBody.length;i<len;i++){
						d.push(dataBody[i].slice(1))
					}
					return d;
				})()
			})

			var dl= dataBody.length,lc=$("#"+op.use_api_box).jQchart.op.line_strokeStyle;
			$('tr:even','#'+id).css('background','#eee');
			if(op.col0color)
			$.each(dataBody,function(i){
				$('tr:nth-child('+dl+'n'+(dl+i+2)%dl+') td:first','#'+id)
					.css('color',lc[i]) 
			})
		}
		return this
	}

})(jQuery);