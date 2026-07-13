export interface CapabilityBase {name:string;version:string;description:string}
export interface SkillCapability extends CapabilityBase {prompt:string;allowed_tools:string[];input_schema:Record<string,unknown>;output_schema:Record<string,unknown>}
export interface PromptCapability extends CapabilityBase {output_mode:'text'|'json';variables:string[]}
export interface ToolCapability extends CapabilityBase {read_only:boolean;input_schema:Record<string,unknown>}
export interface CapabilityResponse {skills:SkillCapability[];prompts:PromptCapability[];tools:ToolCapability[];mcp:{enabled:boolean;protocol_versions:string[];transport:string;methods:string[];remote_default:string}}
