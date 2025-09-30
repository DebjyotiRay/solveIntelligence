interface PatentIssue {
  type: string;
  severity: 'high' | 'medium' | 'low';
  paragraph?: number;
  description: string;
  suggestion: string;
  target?: {
    text?: string;           
    position?: number;       
    pattern?: string;        
    context?: string;        
  };
  replacement?: {
    type: 'add' | 'replace' | 'insert';
    text: string;           
    position?: 'before' | 'after' | 'replace';
  };
}

interface SuggestionLocation {
  position: number;
  length: number;
  originalText: string;
  replacementText: string;
  type: 'add' | 'replace' | 'insert';
}

/**
 * Enhanced suggestion positioning logic that works with patent documents
 */
export const findSuggestionPosition = (issue: PatentIssue, editorContent: string): SuggestionLocation | null => {
  // Strategy 1: Use paragraph-based location
  if (issue.paragraph && issue.paragraph > 0) {
    const paragraphPos = findParagraphPosition(editorContent, issue.paragraph);
    if (paragraphPos !== -1) {
      return createSuggestionFromParagraph(issue, editorContent, paragraphPos);
    }
  }

  // Strategy 2: Use explicit target text
  if (issue.target?.text) {
    const textPos = editorContent.indexOf(issue.target.text);
    if (textPos !== -1) {
      return createSuggestionFromText(issue, editorContent, textPos);
    }
  }

  // Strategy 3: Use regex pattern
  if (issue.target?.pattern) {
    const match = new RegExp(issue.target.pattern, 'i').exec(editorContent);
    if (match) {
      return createSuggestionFromMatch(issue, editorContent, match);
    }
  }

  // Strategy 4: Intelligent type-based detection
  return findByIssueType(issue, editorContent);
};

/**
 * Find paragraph position in content
 */
const findParagraphPosition = (content: string, paragraphNum: number): number => {
  // Split by double newlines or paragraph markers
  const paragraphs = content.split(/\n\s*\n|\r\n\s*\r\n/);
  
  if (paragraphNum <= paragraphs.length && paragraphNum > 0) {
    const precedingParagraphs = paragraphs.slice(0, paragraphNum - 1);
    const precedingText = precedingParagraphs.join('\n\n');
    return precedingText.length + (precedingText ? 2 : 0);
  }
  
  return -1;
};

/**
 * Create suggestion from paragraph positioning
 */
const createSuggestionFromParagraph = (issue: PatentIssue, content: string, paragraphStart: number): SuggestionLocation => {
  // Find the end of this paragraph
  const nextDoubleNewline = content.indexOf('\n\n', paragraphStart);
  const paragraphEnd = nextDoubleNewline === -1 ? content.length : nextDoubleNewline;
  
  // For punctuation issues, focus on the end of the paragraph
  if (issue.type.includes('punctuation')) {
    const paragraphContent = content.substring(paragraphStart, paragraphEnd).trim();
    
    // Check if it ends with a period
    if (!paragraphContent.endsWith('.')) {
      return {
        position: paragraphEnd - (content.length - paragraphEnd === 0 ? 0 : 1),
        length: 0,
        originalText: '',
        replacementText: '.',
        type: 'add'
      };
    }
  }
  
  // For other issues, suggest replacement at paragraph level
  return {
    position: paragraphStart,
    length: paragraphEnd - paragraphStart,
    originalText: content.substring(paragraphStart, paragraphEnd),
    replacementText: extractReplacementText(issue),
    type: 'replace'
  };
};

/**
 * Create suggestion from specific text match
 */
const createSuggestionFromText = (issue: PatentIssue, content: string, textPos: number): SuggestionLocation => {
  const targetText = issue.target!.text!;
  
  return {
    position: textPos,
    length: targetText.length,
    originalText: targetText,
    replacementText: extractReplacementText(issue),
    type: issue.replacement?.type || 'replace'
  };
};

/**
 * Create suggestion from regex match
 */
const createSuggestionFromMatch = (issue: PatentIssue, content: string, match: RegExpExecArray): SuggestionLocation => {
  return {
    position: match.index,
    length: match[0].length,
    originalText: match[0],
    replacementText: extractReplacementText(issue),
    type: issue.replacement?.type || 'replace'
  };
};

/**
 * Smart detection based on issue type
 */
const findByIssueType = (issue: PatentIssue, content: string): SuggestionLocation | null => {
  const issueType = issue.type.toLowerCase();

  // Handle punctuation issues
  if (issueType.includes('punctuation')) {
    return findPunctuationIssue(issue, content);
  }

  // Handle antecedent basis issues
  if (issueType.includes('antecedent') || issueType.includes('basis')) {
    return findAntecedentIssue(issue, content);
  }

  // Handle claim issues
  if (issueType.includes('claim')) {
    return findClaimIssue(issue, content);
  }

  return null;
};

/**
 * Find punctuation-related issues
 */
const findPunctuationIssue = (issue: PatentIssue, content: string): SuggestionLocation | null => {
  const suggestion = issue.suggestion.toLowerCase();
  const description = issue.description.toLowerCase();
  
  // Determine what punctuation to add
  let punctuation = '.';
  if (suggestion.includes('semicolon') || description.includes('semicolon')) {
    punctuation = ';';
  } else if (suggestion.includes('comma') || description.includes('comma')) {
    punctuation = ',';
  }

  // If we have a specific claim mentioned, target that
  const claimMatch = description.match(/claim (\d+)/i);
  if (claimMatch) {
    const claimNumber = parseInt(claimMatch[1]);
    const claimPattern = new RegExp(`claim ${claimNumber}[^]*?(?=claim \\d+|$)`, 'gi');
    const match = claimPattern.exec(content);
    if (match) {
      // Find the end of this claim text, skipping any trailing whitespace
      const claimText = match[0].trim();
      const claimStart = match.index;
      const claimEnd = claimStart + claimText.length;
      
      if (!claimText.endsWith('.') && !claimText.endsWith(';')) {
        return {
          position: claimEnd,
          length: 0,
          originalText: '',
          replacementText: punctuation,
          type: 'add'
        };
      }
    }
  }

  // Look for any sentence/line that ends abruptly without punctuation
  const lines = content.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.length > 10 && !line.endsWith('.') && !line.endsWith(';') && !line.endsWith(':')) {
      // Found a line that should probably end with punctuation
      const lineStart = content.indexOf(line);
      if (lineStart !== -1) {
        return {
          position: lineStart + line.length,
          length: 0,
          originalText: '',
          replacementText: punctuation,
          type: 'add'
        };
      }
    }
  }

  return null;
};

/**
 * Find antecedent basis issues
 */
const findAntecedentIssue = (issue: PatentIssue, content: string): SuggestionLocation | null => {
  const description = issue.description.toLowerCase();
  const suggestion = issue.suggestion.toLowerCase();
  
  // Extract problematic phrase from description
  // Common patterns: "introduces 'a device'", "refers to 'the method'", etc.
  const phraseMatch = description.match(/'([^']+)'/);
  if (phraseMatch) {
    const problematicPhrase = phraseMatch[1];
    const phraseIndex = content.toLowerCase().indexOf(problematicPhrase.toLowerCase());
    if (phraseIndex !== -1) {
      return {
        position: phraseIndex,
        length: problematicPhrase.length,
        originalText: content.substring(phraseIndex, phraseIndex + problematicPhrase.length),
        replacementText: extractReplacementText(issue),
        type: 'replace'
      };
    }
  }

  // Look for common problematic phrases
  const problematicPatterns = [
    /\ba device\b/gi,
    /\bthe device\b/gi,
    /\ban apparatus\b/gi,
    /\bthe apparatus\b/gi,
    /\ba method\b/gi,
    /\bthe method\b/gi,
    /\ba system\b/gi,
    /\bthe system\b/gi
  ];

  for (const pattern of problematicPatterns) {
    const match = pattern.exec(content);
    if (match) {
      return {
        position: match.index,
        length: match[0].length,
        originalText: match[0],
        replacementText: extractReplacementText(issue),
        type: 'replace'
      };
    }
  }

  return null;
};

/**
 * Find claim-related issues
 */
const findClaimIssue = (issue: PatentIssue, content: string): SuggestionLocation | null => {
  // Look for claim structures that might need improvement
  const claimPattern = /Claim \d+[^]*?(?=Claim \d+|$)/gi;
  const matches = Array.from(content.matchAll(claimPattern));

  if (matches.length > 0) {
    const firstClaim = matches[0];
    return {
      position: firstClaim.index!,
      length: firstClaim[0].length,
      originalText: firstClaim[0],
      replacementText: extractReplacementText(issue),
      type: 'replace'
    };
  }

  return null;
};

/**
 * Extract replacement text from issue
 */
const extractReplacementText = (issue: PatentIssue): string => {
  // If explicit replacement is provided
  if (issue.replacement?.text) {
    return issue.replacement.text;
  }

  // Try to extract from suggestion text
  const suggestion = issue.suggestion.toLowerCase();
  
  // For punctuation suggestions
  if (suggestion.includes('add a period') || suggestion.includes('end with a period')) {
    return '.';
  }
  
  if (suggestion.includes('add a comma')) {
    return ',';
  }

  if (suggestion.includes('add a semicolon')) {
    return ';';
  }

  // For antecedent basis suggestions
  if (suggestion.includes('clarify') || suggestion.includes('specify')) {
    return '[specify what this refers to]';
  }

  // Default fallback
  return '[apply suggestion]';
};

/**
 * Generate a unique ID for a suggestion based on issue and index
 */
export const generateSuggestionId = (issue: PatentIssue, index: number): string => {
  return `${issue.type}-${issue.severity}-${index}`;
};

/**
 * Create enhanced issue data with positioning information
 */
export const enhanceIssueWithTargetInfo = (issue: PatentIssue, content: string): PatentIssue => {
  const location = findSuggestionPosition(issue, content);
  
  if (location) {
    return {
      ...issue,
      target: {
        ...issue.target,
        position: location.position,
        text: location.originalText
      },
      replacement: {
        ...issue.replacement,
        type: location.type,
        text: location.replacementText
      }
    };
  }

  return issue;
};
