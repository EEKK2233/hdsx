import{describe,expect,it}from'vitest'
import{renderMarkdown}from'./markdown'
describe('renderMarkdown',()=>{
  it('renders headings lists and emphasis',()=>{const html=renderMarkdown('# 教案\n\n- **目标**\n- 重点');expect(html).toContain('<h1>教案</h1>');expect(html).toContain('<ul>');expect(html).toContain('<strong>目标</strong>')})
  it('escapes raw html and rejects unsafe links',()=>{const html=renderMarkdown('<script>alert(1)</script> [x](javascript:alert(1))');expect(html).not.toContain('<script>');expect(html).not.toContain('href="javascript:')})
})
