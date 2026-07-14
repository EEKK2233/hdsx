export function renderMarkdown(source:string):string{
  const lines=String(source||'').replace(/\r\n?/g,'\n').split('\n'),output:string[]=[]
  const escape=(value:string)=>value.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')
  const inline=(value:string)=>{
    let text=escape(value)
    text=text.replace(/`([^`]+)`/g,'<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g,'<em>$1</em>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g,(_,label,url)=>/^(https?:\/\/|#|\/)/i.test(url)?`<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`:label)
    return text
  }
  const structural=(line:string,index:number)=>/^\s*(```|#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|---+\s*$)/.test(line)||(line.includes('|')&&/^\s*\|?\s*:?-+/.test(lines[index+1]||''))
  for(let index=0;index<lines.length;){
    const line=lines[index]
    if(/^\s*```/.test(line)){const language=escape(line.replace(/^\s*```/,'').trim()),code:string[]=[];index++;while(index<lines.length&&!/^\s*```/.test(lines[index]))code.push(lines[index++]);index++;output.push(`<pre><code${language?` class="language-${language}"`:''}>${escape(code.join('\n'))}</code></pre>`);continue}
    const heading=line.match(/^(#{1,6})\s+(.+)$/);if(heading){const level=heading[1].length;output.push(`<h${level}>${inline(heading[2])}</h${level}>`);index++;continue}
    if(/^\s*---+\s*$/.test(line)){output.push('<hr>');index++;continue}
    if(line.includes('|')&&/^\s*\|?\s*:?-+/.test(lines[index+1]||'')){const rows:string[][]=[];rows.push(line.split('|').map(x=>x.trim()).filter(Boolean));index+=2;while(index<lines.length&&lines[index].includes('|'))rows.push(lines[index++].split('|').map(x=>x.trim()).filter(Boolean));output.push(`<table><thead><tr>${rows[0].map(x=>`<th>${inline(x)}</th>`).join('')}</tr></thead><tbody>${rows.slice(1).map(row=>`<tr>${row.map(x=>`<td>${inline(x)}</td>`).join('')}</tr>`).join('')}</tbody></table>`);continue}
    if(/^\s*[-*+]\s+/.test(line)){const items:string[]=[];while(index<lines.length&&/^\s*[-*+]\s+/.test(lines[index]))items.push(lines[index++].replace(/^\s*[-*+]\s+/,''));output.push(`<ul>${items.map(x=>`<li>${inline(x)}</li>`).join('')}</ul>`);continue}
    if(/^\s*\d+[.)]\s+/.test(line)){const items:string[]=[];while(index<lines.length&&/^\s*\d+[.)]\s+/.test(lines[index]))items.push(lines[index++].replace(/^\s*\d+[.)]\s+/,''));output.push(`<ol>${items.map(x=>`<li>${inline(x)}</li>`).join('')}</ol>`);continue}
    if(/^\s*>\s?/.test(line)){const items:string[]=[];while(index<lines.length&&/^\s*>\s?/.test(lines[index]))items.push(lines[index++].replace(/^\s*>\s?/,''));output.push(`<blockquote>${items.map(inline).join('<br>')}</blockquote>`);continue}
    if(!line.trim()){index++;continue}
    const paragraph=[line.trim()];index++;while(index<lines.length&&lines[index].trim()&&!structural(lines[index],index))paragraph.push(lines[index++].trim());output.push(`<p>${inline(paragraph.join(' '))}</p>`)
  }
  return output.join('\n')
}
